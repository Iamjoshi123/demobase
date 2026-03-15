import json

import pytest

from app.browser.driver import ActionResult, BrowserDriver
from app.browser import executor
from app.models.credential import SandboxLock
from app.models.recipe import DemoRecipe
from app.models.workspace import Workspace
from sqlmodel import select


class FakeDriver(BrowserDriver):
    def __init__(self):
        self.calls = []

    async def start(self, headless: bool = True) -> None:
        self.calls.append(("start", headless))

    async def navigate(self, url: str) -> ActionResult:
        self.calls.append(("navigate", url))
        return ActionResult(success=True, action_type="navigate", target=url, narration=f"Visited {url}")

    async def click(self, selector: str) -> ActionResult:
        self.calls.append(("click", selector))
        return ActionResult(success=True, action_type="click", target=selector)

    async def type_text(self, selector: str, text: str) -> ActionResult:
        self.calls.append(("type", selector, text))
        return ActionResult(success=True, action_type="type", target=selector, value=text)

    async def screenshot(self) -> ActionResult:
        self.calls.append(("screenshot",))
        return ActionResult(success=True, action_type="screenshot", screenshot_b64="abc123", page_url="https://app.example.com")

    async def get_page_state(self) -> dict:
        self.calls.append(("state",))
        return {"url": "https://app.example.com", "title": "App", "visible_text": "Dashboard"}

    async def wait(self, ms: int = 1000) -> ActionResult:
        self.calls.append(("wait", ms))
        return ActionResult(success=True, action_type="wait", value=str(ms), duration_ms=ms)

    async def scroll(self, direction: str = "down") -> ActionResult:
        self.calls.append(("scroll", direction))
        return ActionResult(success=True, action_type="scroll", value=direction)

    async def ai_act(self, instruction: str) -> ActionResult:
        self.calls.append(("ai_act", instruction))
        return ActionResult(success=True, action_type="ai_act", target=instruction, narration=f"AI action: {instruction}")

    async def close(self) -> None:
        self.calls.append(("close",))


def test_acquire_credential_creates_lock(session, demo_session, credential_factory):
    credential = credential_factory(label="demo-user-1")

    acquired = executor._acquire_credential(session, demo_session)

    assert acquired.id == credential.id
    locks = session.exec(select(SandboxLock)).all()
    assert len(locks) == 1
    assert locks[0].credential_id == credential.id
    assert locks[0].is_active is True


def test_acquire_credential_rejects_when_all_credentials_are_locked(session, demo_session, credential_factory):
    credential = credential_factory()
    executor._acquire_credential(session, demo_session)

    blocked = executor._acquire_credential(session, demo_session)

    assert blocked is None
    locks = session.exec(select(SandboxLock).where(SandboxLock.credential_id == credential.id)).all()
    assert len(locks) == 1


def test_release_credential_marks_lock_inactive(session, demo_session, credential_factory):
    credential_factory()
    executor._acquire_credential(session, demo_session)

    executor._release_credential(session, demo_session.id)

    lock = session.exec(select(SandboxLock)).first()
    assert lock.is_active is False
    assert lock.released_at is not None


@pytest.mark.asyncio
async def test_execute_step_dispatches_to_driver_methods():
    driver = FakeDriver()

    navigate = await executor._execute_step(driver, "navigate", "https://app.example.com")
    click = await executor._execute_step(driver, "click", "#submit")
    typed = await executor._execute_step(driver, "type", "#email", "buyer@example.com")
    ai_action = await executor._execute_step(driver, "ai_act", "Open the analytics dashboard")
    narrate = await executor._execute_step(driver, "narrate", value="Explaining dashboard")
    unknown = await executor._execute_step(driver, "unknown")

    assert navigate.success is True
    assert click.success is True
    assert typed.value == "buyer@example.com"
    assert ai_action.narration == "AI action: Open the analytics dashboard"
    assert narrate.narration == "Explaining dashboard"
    assert unknown.success is False
    assert unknown.error == "Unknown action: unknown"


@pytest.mark.asyncio
async def test_execute_recipe_runs_all_steps_and_logs_results(session, demo_session):
    driver = FakeDriver()
    recipe = DemoRecipe(
        workspace_id=demo_session.workspace_id,
        name="Multi-step",
        steps_json=json.dumps(
            [
                {"action": "navigate", "target": "https://app.example.com/dashboard", "description": "Open dashboard", "wait_ms": 0},
                {"action": "click", "target": "#reports", "wait_ms": 25},
                {"action": "screenshot", "wait_ms": 0},
            ]
        ),
    )
    executor._active_sessions[demo_session.id] = driver

    try:
        results = await executor.execute_recipe(session, demo_session.id, recipe)
    finally:
        executor._active_sessions.clear()

    assert [result.action_type for result in results] == ["navigate", "click", "screenshot"]
    assert results[0].narration == "Open dashboard"
    assert driver.calls == [
        ("navigate", "https://app.example.com/dashboard"),
        ("click", "#reports"),
        ("wait", 25),
        ("screenshot",),
    ]


@pytest.mark.asyncio
async def test_execute_recipe_returns_empty_for_invalid_json(session, demo_session):
    driver = FakeDriver()
    recipe = DemoRecipe(workspace_id=demo_session.workspace_id, name="Broken", steps_json="{invalid")
    executor._active_sessions[demo_session.id] = driver

    try:
        results = await executor.execute_recipe(session, demo_session.id, recipe)
    finally:
        executor._active_sessions.clear()

    assert results == []


@pytest.mark.asyncio
async def test_start_browser_session_bootstraps_public_url_without_credentials(session, demo_session, monkeypatch):
    workspace = session.get(Workspace, demo_session.workspace_id)
    workspace.product_url = "https://public.example.com/demo"
    workspace.browser_auth_mode = "credentials"
    session.add(workspace)
    session.commit()

    driver = FakeDriver()
    monkeypatch.setattr(executor, "_create_driver", lambda: driver)

    credential_id = await executor.start_browser_session(session, demo_session)

    assert credential_id == "no-auth"
    assert ("navigate", "https://public.example.com/demo") in driver.calls
