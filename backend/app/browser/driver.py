"""Browser driver abstraction with Playwright implementation.

Provides BrowserDriver interface and PlaywrightDriver concrete implementation.
Optional BrowserUseDriver can be enabled via env var.
"""

import asyncio
import base64
import logging
import socket
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional
from pathlib import Path

from app.browser.stagehand_adapter import StagehandAdapter

logger = logging.getLogger(__name__)

FrameConsumer = Callable[[bytes, int, int], Awaitable[None]]
DEFAULT_NAVIGATION_TIMEOUT_MS = 90000


@dataclass
class ActionResult:
    success: bool
    action_type: str
    target: Optional[str] = None
    value: Optional[str] = None
    screenshot_b64: Optional[str] = None
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    narration: Optional[str] = None
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    telemetry: Optional[dict] = None


class BrowserDriver(ABC):
    """Abstract browser driver interface."""

    @abstractmethod
    async def start(self, headless: bool = True) -> None:
        """Initialize browser and create a new context."""
        pass

    @abstractmethod
    async def navigate(self, url: str) -> ActionResult:
        """Navigate to a URL."""
        pass

    @abstractmethod
    async def click(self, selector: str) -> ActionResult:
        """Click an element by CSS selector."""
        pass

    @abstractmethod
    async def type_text(self, selector: str, text: str) -> ActionResult:
        """Type text into an input field."""
        pass

    @abstractmethod
    async def screenshot(self) -> ActionResult:
        """Capture a screenshot of the current page."""
        pass

    @abstractmethod
    async def get_page_state(self) -> dict:
        """Get current page URL, title, and visible text summary."""
        pass

    @abstractmethod
    async def wait(self, ms: int = 1000) -> ActionResult:
        """Wait for a specified time."""
        pass

    @abstractmethod
    async def scroll(self, direction: str = "down") -> ActionResult:
        """Scroll the page."""
        pass

    async def ai_act(self, instruction: str) -> ActionResult:
        """Use Stagehand or another AI browser layer to perform a natural-language action."""
        return ActionResult(
            success=False,
            action_type="ai_act",
            target=instruction,
            error="AI browser actions are not implemented for this driver",
        )

    async def ai_observe(self, instruction: str) -> list[dict]:
        """Return visible action candidates for a natural-language goal."""
        return []

    async def wait_for_url(self, pattern: str, timeout_ms: int = 15000) -> ActionResult:
        """Wait until the page URL contains the given pattern."""
        return ActionResult(success=False, action_type="wait_for_url", target=pattern, error="Not implemented")

    async def wait_for_text(self, text: str, timeout_ms: int = 15000) -> ActionResult:
        """Wait until visible text appears on the page."""
        return ActionResult(success=False, action_type="wait_for_text", target=text, error="Not implemented")

    async def wait_for_selector(self, selector: str, timeout_ms: int = 15000) -> ActionResult:
        """Wait until a selector is visible on the page."""
        return ActionResult(success=False, action_type="wait_for_selector", target=selector, error="Not implemented")

    async def start_frame_stream(self, on_frame: FrameConsumer) -> None:
        """Start pushing live page frames to the given callback."""
        raise NotImplementedError("Live frame streaming is not supported by this driver")

    async def stop_frame_stream(self) -> None:
        """Stop the active frame stream if one is running."""
        return None

    @abstractmethod
    async def close(self) -> None:
        """Close browser and clean up."""
        pass


class PlaywrightDriver(BrowserDriver):
    """Primary browser driver using Playwright."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._cdp_session = None
        self._frame_listener = None
        self._frame_poller_task: Optional[asyncio.Task[None]] = None
        self._screenshot_dir = Path("data/screenshots")
        self._stagehand = StagehandAdapter()
        self._stagehand_cdp_port: Optional[int] = None

    async def start(self, headless: bool = True) -> None:
        from playwright.async_api import async_playwright
        import httpx
        from app.config import settings

        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        launch_args = []
        if settings.enable_stagehand:
            self._stagehand_cdp_port = _find_available_port(preferred_port=settings.stagehand_cdp_port)
            launch_args.append(f"--remote-debugging-port={self._stagehand_cdp_port}")
        self._browser = await self._playwright.chromium.launch(headless=headless, args=launch_args)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="AgenticDemoBrain/1.0",
        )
        self._page = await self._context.new_page()
        if settings.enable_stagehand:
            try:
                version_info = httpx.get(
                    f"http://127.0.0.1:{self._stagehand_cdp_port}/json/version",
                    timeout=3,
                ).json()
                self._stagehand.set_browser_cdp_url(version_info.get("webSocketDebuggerUrl"))
            except Exception as exc:
                logger.warning("Could not resolve Stagehand CDP URL: %s", exc)
        logger.info("Playwright browser started")

    async def navigate(self, url: str) -> ActionResult:
        start = time.time()
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT_MS)
            duration = int((time.time() - start) * 1000)
            screenshot = await self._take_screenshot()
            return ActionResult(
                success=True,
                action_type="navigate",
                target=url,
                duration_ms=duration,
                screenshot_b64=screenshot,
                page_url=self._page.url,
                page_title=await self._page.title(),
                narration=f"Navigated to {await self._page.title() or url}",
            )
        except Exception as e:
            current_url = ""
            page_title = ""
            with_title = False
            try:
                current_url = self._page.url or ""
            except Exception:
                current_url = ""
            if current_url and current_url != "about:blank":
                try:
                    page_title = await self._page.title()
                    with_title = bool(page_title)
                except Exception:
                    page_title = ""
                screenshot = await self._take_screenshot()
                return ActionResult(
                    success=True,
                    action_type="navigate",
                    target=url,
                    duration_ms=int((time.time() - start) * 1000),
                    screenshot_b64=screenshot,
                    page_url=current_url,
                    page_title=page_title or None,
                    narration=(
                        f"Navigated to {page_title or current_url}. The page is still finishing its initial load."
                        if with_title or current_url
                        else "Navigation started and the page is still loading."
                    ),
                )
            return ActionResult(
                success=False,
                action_type="navigate",
                target=url,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def click(self, selector: str) -> ActionResult:
        start = time.time()
        try:
            await self._page.wait_for_selector(selector, timeout=5000)
            telemetry = await self._selector_telemetry(selector)
            await self._page.click(selector)
            await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            duration = int((time.time() - start) * 1000)
            screenshot = await self._take_screenshot()
            return ActionResult(
                success=True,
                action_type="click",
                target=selector,
                duration_ms=duration,
                screenshot_b64=screenshot,
                page_url=self._page.url,
                page_title=await self._page.title(),
                narration="Clicked on element",
                telemetry=telemetry,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="click",
                target=selector,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def type_text(self, selector: str, text: str) -> ActionResult:
        start = time.time()
        try:
            await self._page.wait_for_selector(selector, timeout=5000)
            telemetry = await self._selector_telemetry(selector)
            if telemetry is None:
                telemetry = {"kind": "type", "selector": selector}
            telemetry["typed_value"] = text
            await self._page.fill(selector, text)
            duration = int((time.time() - start) * 1000)
            screenshot = await self._take_screenshot()
            return ActionResult(
                success=True,
                action_type="type",
                target=selector,
                value=text,
                duration_ms=duration,
                screenshot_b64=screenshot,
                page_url=self._page.url,
                narration="Typed text into field",
                telemetry=telemetry,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="type",
                target=selector,
                value=text,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def screenshot(self) -> ActionResult:
        start = time.time()
        try:
            screenshot = await self._take_screenshot()
            return ActionResult(
                success=True,
                action_type="screenshot",
                duration_ms=int((time.time() - start) * 1000),
                screenshot_b64=screenshot,
                page_url=self._page.url,
                page_title=await self._page.title(),
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="screenshot",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def get_page_state(self) -> dict:
        try:
            title = await self._page.title()
            url = self._page.url
            # Get visible text (limited)
            text = await self._page.evaluate("() => document.body?.innerText?.substring(0, 2000) || ''")
            auth_hint = await self._page.evaluate(
                """() => {
                    const hasPasswordField = Boolean(document.querySelector('input[type="password"]'));
                    const bodyText = (document.body?.innerText || '').toLowerCase();
                    const loginSignals = ['sign in', 'log in', 'login', 'password', 'continue with email'];
                    return hasPasswordField || loginSignals.some((token) => bodyText.includes(token))
                      ? 'login_form'
                      : null;
                }"""
            )
            state = {
                "url": url,
                "title": title,
                "visible_text": text[:1000],
            }
            if auth_hint:
                state["auth_hint"] = auth_hint
            try:
                stagehand_summary = await asyncio.wait_for(self._stagehand.summarize_page(self._page), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Timed out while summarizing live page with Stagehand")
                stagehand_summary = {}
            except Exception as exc:
                logger.warning("Stagehand page summary failed: %s", exc)
                stagehand_summary = {}
            if stagehand_summary:
                state["stagehand_summary"] = stagehand_summary.get("summary")
                state["stagehand_active_module"] = stagehand_summary.get("active_module")
                state["stagehand_primary_actions"] = stagehand_summary.get("primary_actions", [])
                state["stagehand_entities"] = stagehand_summary.get("entities", [])
            return state
        except Exception as e:
            return {"url": "", "title": "", "visible_text": "", "error": str(e)}

    async def wait(self, ms: int = 1000) -> ActionResult:
        await asyncio.sleep(ms / 1000)
        return ActionResult(
            success=True,
            action_type="wait",
            value=str(ms),
            duration_ms=ms,
            narration=f"Waited {ms}ms",
        )

    async def scroll(self, direction: str = "down") -> ActionResult:
        start = time.time()
        try:
            delta = 500 if direction == "down" else -500
            await self._page.mouse.wheel(0, delta)
            await asyncio.sleep(0.5)
            screenshot = await self._take_screenshot()
            return ActionResult(
                success=True,
                action_type="scroll",
                value=direction,
                duration_ms=int((time.time() - start) * 1000),
                screenshot_b64=screenshot,
                narration=f"Scrolled {direction}",
                telemetry={
                    "kind": "scroll",
                    "direction": direction,
                    "x": 640,
                    "y": 360,
                    "delta_y": delta,
                },
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="scroll",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def wait_for_url(self, pattern: str, timeout_ms: int = 15000) -> ActionResult:
        start = time.time()
        try:
            await self._page.wait_for_url(lambda url: pattern in url, timeout=timeout_ms)
            return ActionResult(
                success=True,
                action_type="wait_for_url",
                target=pattern,
                duration_ms=int((time.time() - start) * 1000),
                page_url=self._page.url,
                page_title=await self._page.title(),
                narration=f"Waited for URL containing {pattern}",
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="wait_for_url",
                target=pattern,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def wait_for_text(self, text: str, timeout_ms: int = 15000) -> ActionResult:
        start = time.time()
        try:
            await self._page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout_ms)
            return ActionResult(
                success=True,
                action_type="wait_for_text",
                target=text,
                duration_ms=int((time.time() - start) * 1000),
                page_url=self._page.url,
                page_title=await self._page.title(),
                narration=f"Waited for text {text}",
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="wait_for_text",
                target=text,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def wait_for_selector(self, selector: str, timeout_ms: int = 15000) -> ActionResult:
        start = time.time()
        try:
            await self._page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            return ActionResult(
                success=True,
                action_type="wait_for_selector",
                target=selector,
                duration_ms=int((time.time() - start) * 1000),
                page_url=self._page.url,
                page_title=await self._page.title(),
                narration=f"Waited for selector {selector}",
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="wait_for_selector",
                target=selector,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def start_frame_stream(self, on_frame: FrameConsumer) -> None:
        if not self._page or not self._context:
            raise RuntimeError("Browser is not started")
        if self._frame_poller_task is None or self._frame_poller_task.done():
            self._frame_poller_task = asyncio.create_task(self._poll_frames(on_frame))

    async def _poll_frames(self, on_frame: FrameConsumer) -> None:
        while True:
            try:
                if self._page is None:
                    return
                payload = await self._page.screenshot(type="jpeg", quality=80)
                await on_frame(payload, 1280, 720)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("Frame polling failed: %s", exc)
            await asyncio.sleep(0.25)

    async def stop_frame_stream(self) -> None:
        if self._frame_poller_task is not None:
            self._frame_poller_task.cancel()
            self._frame_poller_task = None
        return

    async def close(self) -> None:
        try:
            await self._stagehand.close()
            await self.stop_frame_stream()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("Playwright browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def _take_screenshot(self) -> Optional[str]:
        """Take a screenshot and return as base64."""
        try:
            raw = await self._page.screenshot(type="jpeg", quality=70)
            return base64.b64encode(raw).decode()
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None

    async def _selector_telemetry(self, selector: str) -> dict | None:
        if self._page is None:
            return None
        try:
            locator = self._page.locator(selector).first
            box = await locator.bounding_box()
            text = await locator.inner_text(timeout=1000)
        except Exception:
            return {"kind": "click", "selector": selector}
        if not box:
            return {"kind": "click", "selector": selector, "label": text[:80] if text else None}
        return {
            "kind": "click",
            "selector": selector,
            "x": box["x"] + box["width"] / 2,
            "y": box["y"] + box["height"] / 2,
            "width": box["width"],
            "height": box["height"],
            "label": text[:80] if text else None,
        }

    async def ai_act(self, instruction: str) -> ActionResult:
        start = time.time()
        try:
            outcome = await self._stagehand.act(self._page, instruction)
            screenshot = await self._take_screenshot()
            telemetry = _stagehand_action_telemetry(outcome)
            return ActionResult(
                success=bool(outcome.get("success")),
                action_type="ai_act",
                target=instruction,
                screenshot_b64=screenshot,
                duration_ms=int((time.time() - start) * 1000),
                page_url=self._page.url if self._page else None,
                page_title=await self._page.title() if self._page else None,
                narration=outcome.get("action_description") or outcome.get("message") or instruction,
                error=outcome.get("error"),
                telemetry=telemetry,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="ai_act",
                target=instruction,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def ai_observe(self, instruction: str) -> list[dict]:
        try:
            return await self._stagehand.observe(self._page, instruction)
        except Exception as e:
            logger.warning("Stagehand observe failed during browser inspection: %s", e)
            return []


class FakeBrowserDriver(BrowserDriver):
    """Deterministic browser driver for test environments."""

    def __init__(self):
        self._url = "about:blank"
        self._title = "Fake Browser"
        self._typed_values: dict[str, str] = {}
        self._started = False

    async def start(self, headless: bool = True) -> None:
        self._started = True
        self._title = "Fake Browser"

    async def navigate(self, url: str) -> ActionResult:
        self._url = url
        self._title = url.rstrip("/").split("/")[-1] or "Home"
        return ActionResult(
            success=True,
            action_type="navigate",
            target=url,
            page_url=self._url,
            page_title=self._title,
            screenshot_b64=self._fake_screenshot(),
            narration=f"Navigated to {url}",
        )

    async def click(self, selector: str) -> ActionResult:
        return ActionResult(
            success=True,
            action_type="click",
            target=selector,
            page_url=self._url,
            page_title=self._title,
            narration=f"Clicked {selector}",
            screenshot_b64=self._fake_screenshot(),
            telemetry={"kind": "click", "selector": selector, "x": 320, "y": 180},
        )

    async def type_text(self, selector: str, text: str) -> ActionResult:
        self._typed_values[selector] = text
        return ActionResult(
            success=True,
            action_type="type",
            target=selector,
            value=text,
            page_url=self._url,
            page_title=self._title,
            narration=f"Typed into {selector}",
            screenshot_b64=self._fake_screenshot(),
            telemetry={"kind": "type", "selector": selector, "x": 320, "y": 180, "typed_value": text},
        )

    async def screenshot(self) -> ActionResult:
        return ActionResult(
            success=True,
            action_type="screenshot",
            screenshot_b64=self._fake_screenshot(),
            page_url=self._url,
            page_title=self._title,
        )

    async def get_page_state(self) -> dict:
        return {
            "url": self._url,
            "title": self._title,
            "visible_text": "Fake browser content for integration testing.",
            "stagehand_summary": "Fake screen summary for testing.",
            "stagehand_active_module": "Fake Module",
            "stagehand_primary_actions": ["Open dashboard", "Filter results"],
            "stagehand_entities": ["Demo account"],
            "typed_values": dict(self._typed_values),
        }

    async def wait(self, ms: int = 1000) -> ActionResult:
        return ActionResult(success=True, action_type="wait", value=str(ms), duration_ms=ms)

    async def scroll(self, direction: str = "down") -> ActionResult:
        return ActionResult(
            success=True,
            action_type="scroll",
            value=direction,
            page_url=self._url,
            page_title=self._title,
            narration=f"Scrolled {direction}",
            screenshot_b64=self._fake_screenshot(),
            telemetry={"kind": "scroll", "direction": direction, "x": 320, "y": 180, "delta_y": 500 if direction == "down" else -500},
        )

    async def wait_for_url(self, pattern: str, timeout_ms: int = 15000) -> ActionResult:
        matches = pattern in self._url
        return ActionResult(
            success=matches,
            action_type="wait_for_url",
            target=pattern,
            page_url=self._url,
            page_title=self._title,
            narration=f"Matched URL {pattern}" if matches else None,
            error=None if matches else f"URL does not contain {pattern}",
        )

    async def wait_for_text(self, text: str, timeout_ms: int = 15000) -> ActionResult:
        visible_text = "Fake browser content for integration testing."
        matches = text.lower() in visible_text.lower()
        return ActionResult(
            success=matches,
            action_type="wait_for_text",
            target=text,
            page_url=self._url,
            page_title=self._title,
            narration=f"Matched text {text}" if matches else None,
            error=None if matches else f"Visible text does not contain {text}",
        )

    async def wait_for_selector(self, selector: str, timeout_ms: int = 15000) -> ActionResult:
        return ActionResult(
            success=True,
            action_type="wait_for_selector",
            target=selector,
            page_url=self._url,
            page_title=self._title,
            narration=f"Selector {selector} is ready",
        )

    async def start_frame_stream(self, on_frame: FrameConsumer) -> None:
        await on_frame(base64.b64decode(self._fake_screenshot()), 1280, 720)

    async def ai_act(self, instruction: str) -> ActionResult:
        return ActionResult(
            success=True,
            action_type="ai_act",
            target=instruction,
            page_url=self._url,
            page_title=self._title,
            narration=f"Stagehand executed: {instruction}",
            screenshot_b64=self._fake_screenshot(),
            telemetry={"kind": "click", "selector": "fake-stagehand", "x": 320, "y": 180, "label": instruction},
        )

    async def close(self) -> None:
        self._started = False

    def _fake_screenshot(self) -> str:
        return base64.b64encode(b"fake-browser-screenshot").decode()


def _find_available_port(preferred_port: int) -> int:
    for candidate in (preferred_port, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return int(sock.getsockname()[1])
    raise RuntimeError("Could not allocate a remote debugging port for Stagehand")


def _stagehand_action_telemetry(outcome: dict) -> dict | None:
    actions = outcome.get("actions")
    if not isinstance(actions, list) or not actions:
        return None
    candidate = actions[0] if isinstance(actions[0], dict) else {}
    telemetry: dict[str, object] = {
        "kind": str(candidate.get("type") or candidate.get("method") or "click"),
        "selector": candidate.get("selector"),
        "label": candidate.get("description") or candidate.get("text") or candidate.get("action"),
    }
    for key in ("x", "y", "width", "height"):
        value = candidate.get(key)
        if isinstance(value, (int, float)):
            telemetry[key] = value
    box = candidate.get("bbox")
    if isinstance(box, dict):
        x = box.get("x")
        y = box.get("y")
        width = box.get("width")
        height = box.get("height")
        if isinstance(x, (int, float)):
            telemetry["x"] = x + (float(width) / 2 if isinstance(width, (int, float)) else 0)
        if isinstance(y, (int, float)):
            telemetry["y"] = y + (float(height) / 2 if isinstance(height, (int, float)) else 0)
        if isinstance(width, (int, float)):
            telemetry["width"] = width
        if isinstance(height, (int, float)):
            telemetry["height"] = height
    return telemetry
