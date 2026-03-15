"""Browser execution engine - runs recipes and exploratory actions."""

import json
import logging
from typing import Optional
from sqlmodel import Session, select
from app.browser.driver import PlaywrightDriver, FakeBrowserDriver, BrowserDriver, ActionResult
from app.models.session import BrowserAction, DemoSession
from app.models.credential import SandboxCredential, SandboxLock
from app.models.recipe import DemoRecipe
from app.models.workspace import Workspace
from app.services.encryption import decrypt
from app.config import settings
from app.policies.engine import evaluate_policy

logger = logging.getLogger(__name__)

# In-memory registry of active browser sessions
_active_sessions: dict[str, BrowserDriver] = {}


def _create_driver() -> BrowserDriver:
    if settings.app_env == "test":
        return FakeBrowserDriver()
    return PlaywrightDriver()


def get_active_driver(session_id: str) -> Optional[BrowserDriver]:
    return _active_sessions.get(session_id)


async def start_browser_session(
    db: Session,
    session: DemoSession,
) -> Optional[str]:
    """Start an isolated browser context and acquire a credential lock.

    Returns the credential_id if successful, None on failure.
    """
    workspace = db.get(Workspace, session.workspace_id)
    auth_mode = workspace.browser_auth_mode if workspace else "credentials"
    credential = None
    if auth_mode != "none":
        credential = _acquire_credential(db, session)
        if not credential:
            logger.info(
                "No available credentials for workspace %s; continuing in read-only mode",
                session.workspace_id,
            )

    # Start browser
    driver = _create_driver()
    try:
        await driver.start(headless=settings.playwright_headless)
    except Exception as e:
        logger.error(f"Failed to start browser: {e}")
        _release_credential(db, session.id)
        return None

    _active_sessions[session.id] = driver

    session.credential_id = None
    if credential is not None:
        login_result = await _login(driver, credential)
        _log_action(db, session.id, login_result)
        if not login_result.success:
            logger.error(f"Login failed: {login_result.error}")
        else:
            session.credential_id = credential.id

    bootstrap_target = workspace.product_url if workspace and workspace.product_url else None
    if bootstrap_target:
        should_bootstrap = credential is None or credential.login_url.rstrip("/") != bootstrap_target.rstrip("/")
        if should_bootstrap:
            bootstrap_result = await driver.navigate(bootstrap_target)
            _log_action(db, session.id, bootstrap_result)
            if not bootstrap_result.success:
                logger.error(f"Bootstrap navigation failed: {bootstrap_result.error}")
                await close_browser_session(db, session.id)
                return None

    if credential is None:
        session.credential_id = None
    else:
        session.credential_id = credential.id

    session.browser_session_id = session.id
    db.add(session)
    db.commit()

    return credential.id if credential else "no-auth"


async def execute_recipe(
    db: Session,
    session_id: str,
    recipe: DemoRecipe,
) -> list[ActionResult]:
    """Execute a demo recipe step by step."""
    driver = _active_sessions.get(session_id)
    if not driver:
        logger.error(f"No active browser for session {session_id}")
        return []

    try:
        steps = json.loads(recipe.steps_json)
    except json.JSONDecodeError:
        logger.error(f"Invalid recipe steps JSON for recipe {recipe.id}")
        return []

    results = []
    for step in steps:
        result = await execute_recipe_step(db, session_id, step)
        results.append(result)

    return results


async def execute_action(
    db: Session,
    session_id: str,
    action: str,
    target: Optional[str] = None,
    value: Optional[str] = None,
) -> ActionResult:
    """Execute a single browser action."""
    driver = _active_sessions.get(session_id)
    if not driver:
        return ActionResult(success=False, action_type=action, error="No active browser session")

    blocked = _enforce_action_policy(db, session_id, action, target)
    if blocked is not None:
        _log_action(db, session_id, blocked)
        return blocked

    before_state = await driver.get_page_state()
    result = await _execute_step(driver, action, target, value)
    if result.success:
        after_state = await driver.get_page_state()
        from app.runtime_v3.pipeline import build_verified_narration

        result.narration = build_verified_narration(
            action_type=action,
            target=target,
            before_state=before_state,
            after_state=after_state,
            fallback_narration=result.narration,
        )
    _log_action(db, session_id, result)
    return result


async def execute_recipe_step(
    db: Session,
    session_id: str,
    step: dict,
) -> ActionResult:
    driver = _active_sessions.get(session_id)
    if not driver:
        return ActionResult(success=False, action_type=step.get("action", ""), error="No active browser session")

    action = step.get("action", "")
    target = step.get("target", "")
    value = step.get("value", "")
    wait_ms = step.get("wait_ms", 1000)

    blocked = _enforce_action_policy(db, session_id, action, target)
    if blocked is not None:
        blocked.narration = step.get("description", blocked.narration)
        _log_action(db, session_id, blocked)
        return blocked

    before_state = await driver.get_page_state()
    result = await _execute_step(driver, action, target, value)
    if result.success:
        after_state = await driver.get_page_state()
        from app.runtime_v3.pipeline import build_verified_narration

        result.narration = build_verified_narration(
            action_type=action,
            target=target,
            before_state=before_state,
            after_state=after_state,
            fallback_narration=step.get("description") or result.narration,
        )
    else:
        result.narration = step.get("description", result.narration)
    _log_action(db, session_id, result)

    if not result.success:
        logger.warning(f"Recipe step failed: {action} {target} - {result.error}")

    if wait_ms > 0:
        await driver.wait(wait_ms)

    return result


async def get_browser_state(session_id: str) -> Optional[dict]:
    """Get current browser page state for a session."""
    driver = _active_sessions.get(session_id)
    if not driver:
        return None
    return await driver.get_page_state()


async def observe_action_candidates(session_id: str, instruction: str) -> list[dict]:
    """Return Stagehand-observed visible action candidates for the current page."""
    driver = _active_sessions.get(session_id)
    if not driver:
        return []
    return await driver.ai_observe(instruction)


async def take_screenshot(session_id: str) -> Optional[str]:
    """Take a screenshot and return base64."""
    driver = _active_sessions.get(session_id)
    if not driver:
        return None
    result = await driver.screenshot()
    return result.screenshot_b64 if result.success else None


async def close_browser_session(db: Session, session_id: str) -> None:
    """Close browser and release credential lock."""
    driver = _active_sessions.pop(session_id, None)
    if driver:
        await driver.close()
    _release_credential(db, session_id)
    logger.info(f"Browser session closed for {session_id}")


def _acquire_credential(db: Session, session: DemoSession) -> Optional[SandboxCredential]:
    """Find and lock an available credential for this workspace."""
    # Get all active credentials
    credentials = db.exec(
        select(SandboxCredential).where(
            SandboxCredential.workspace_id == session.workspace_id,
            SandboxCredential.is_active,
        )
    ).all()

    for cred in credentials:
        # Check if already locked
        active_lock = db.exec(
            select(SandboxLock).where(
                SandboxLock.credential_id == cred.id,
                SandboxLock.is_active,
            )
        ).first()

        if active_lock is None:
            # Acquire lock
            lock = SandboxLock(
                credential_id=cred.id,
                session_id=session.id,
                is_active=True,
            )
            db.add(lock)
            db.commit()
            logger.info(f"Acquired credential lock: {cred.label}")
            return cred

    return None


def _release_credential(db: Session, session_id: str) -> None:
    """Release credential lock for a session."""
    from datetime import datetime, timezone
    locks = db.exec(
        select(SandboxLock).where(
            SandboxLock.session_id == session_id,
            SandboxLock.is_active,
        )
    ).all()
    for lock in locks:
        lock.is_active = False
        lock.released_at = datetime.now(timezone.utc)
        db.add(lock)
    db.commit()


def _enforce_action_policy(
    db: Session,
    session_id: str,
    action: str,
    target: Optional[str],
) -> Optional[ActionResult]:
    """Reject browser actions that violate workspace policies."""
    session = db.get(DemoSession, session_id)
    if not session:
        return ActionResult(success=False, action_type=action, target=target, error="Session not found")

    decision = evaluate_policy(
        db=db,
        workspace_id=session.workspace_id,
        user_message=target if action == "ai_act" else "",
        proposed_action=f"{action} {target or ''}".strip(),
        target_url=target if action == "navigate" else None,
    )
    if decision.allowed or decision.decision == "warn":
        return None

    return ActionResult(
        success=False,
        action_type=action,
        target=target,
        error=decision.reason or f"Blocked by policy: {decision.decision}",
        narration=f"Blocked by policy: {decision.decision}",
    )


async def _login(driver: BrowserDriver, credential: SandboxCredential) -> ActionResult:
    """Perform login using decrypted credentials."""
    try:
        username = decrypt(credential.username_encrypted)
        password = decrypt(credential.password_encrypted)
    except ValueError as e:
        return ActionResult(success=False, action_type="login", error=str(e))

    # Navigate to login URL
    nav_result = await driver.navigate(credential.login_url)
    if not nav_result.success:
        return nav_result

    # Try common login selectors
    username_selectors = [
        'input[name="username"]', 'input[name="email"]', 'input[type="email"]',
        '#username', '#email', 'input[name="login"]', 'input[placeholder*="email" i]',
        'input[placeholder*="username" i]',
    ]
    password_selectors = [
        'input[name="password"]', 'input[type="password"]', '#password',
    ]
    submit_selectors = [
        'button[type="submit"]', 'input[type="submit"]', 'button:has-text("Log in")',
        'button:has-text("Sign in")', 'button:has-text("Login")',
    ]

    # Type username
    for sel in username_selectors:
        result = await driver.type_text(sel, username)
        if result.success:
            break
    else:
        return ActionResult(success=False, action_type="login", error="Could not find username field")

    # Type password
    for sel in password_selectors:
        result = await driver.type_text(sel, password)
        if result.success:
            break
    else:
        return ActionResult(success=False, action_type="login", error="Could not find password field")

    # Click submit
    for sel in submit_selectors:
        result = await driver.click(sel)
        if result.success:
            break
    else:
        return ActionResult(success=False, action_type="login", error="Could not find submit button")

    await driver.wait(2000)
    screenshot = await driver.screenshot()

    return ActionResult(
        success=True,
        action_type="login",
        narration="Successfully logged in",
        screenshot_b64=screenshot.screenshot_b64 if screenshot.success else None,
        page_url=screenshot.page_url,
        page_title=screenshot.page_title,
    )


async def _execute_step(
    driver: BrowserDriver,
    action: str,
    target: Optional[str] = None,
    value: Optional[str] = None,
) -> ActionResult:
    """Execute a single browser action step."""
    if action == "navigate" and target:
        return await driver.navigate(target)
    elif action == "click" and target:
        return await driver.click(target)
    elif action == "type" and target and value:
        return await driver.type_text(target, value)
    elif action == "screenshot":
        return await driver.screenshot()
    elif action == "wait":
        return await driver.wait(int(value or 1000))
    elif action == "scroll":
        return await driver.scroll(value or "down")
    elif action == "wait_for_url" and target:
        return await driver.wait_for_url(target, int(value or 15000))
    elif action == "wait_for_text" and target:
        return await driver.wait_for_text(target, int(value or 15000))
    elif action == "wait_for_selector" and target:
        return await driver.wait_for_selector(target, int(value or 15000))
    elif action == "ai_act" and target:
        return await driver.ai_act(target)
    elif action == "narrate":
        return ActionResult(
            success=True,
            action_type="narrate",
            narration=value or "",
        )
    else:
        return ActionResult(
            success=False,
            action_type=action,
            error=f"Unknown action: {action}",
        )


def _log_action(db: Session, session_id: str, result: ActionResult) -> None:
    """Persist a browser action to the audit trail."""
    action = BrowserAction(
        session_id=session_id,
        action_type=result.action_type,
        target=result.target,
        value=result.value,
        status="success" if result.success else "error",
        screenshot_path=result.screenshot_path,
        error_message=result.error,
        narration=result.narration,
        duration_ms=result.duration_ms,
    )
    db.add(action)
    db.commit()
