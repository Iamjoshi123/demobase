import asyncio
import types

import pytest

from app.live.room import LiveKitParticipantContract
from app.live.runtime import LiveDemoRuntime
from app.browser.driver import ActionResult
from app.models.session import DemoSession
from app.models.workspace import Workspace
from sqlmodel import Session


class _RetryingMediaPublisher:
    def __init__(self) -> None:
        self.start_attempts = 0
        self.stop_called = False
        self.ready = asyncio.Event()
        self.spoken: list[str] = []

    async def start(
        self,
        driver,
        agent_contract,
        browser_contract=None,
        on_transcript=None,
        on_speech_activity=None,
        on_startup_state=None,
    ) -> None:
        self.start_attempts += 1
        if self.start_attempts < 2:
            raise RuntimeError("room attach timed out")
        if on_startup_state is not None:
            await on_startup_state("room_connected", "connected")
            await on_startup_state("agent_audio_ready", "agent audio ready")
            await on_startup_state("browser_publisher_ready", "browser publisher ready")
            await on_startup_state("buyer_audio_ready", "buyer audio ready")
        self.ready.set()

    async def speak(self, text: str) -> None:
        self.spoken.append(text)

    async def stop(self) -> None:
        self.stop_called = True


class _ExplodingMediaPublisher:
    async def start(
        self,
        driver,
        agent_contract,
        browser_contract=None,
        on_transcript=None,
        on_speech_activity=None,
        on_startup_state=None,
    ) -> None:
        return None

    async def speak(self, text: str) -> None:
        raise RuntimeError("speaker pipeline exploded")

    async def stop(self) -> None:
        return None


@pytest.mark.asyncio
async def test_live_runtime_start_returns_before_media_attaches(session, monkeypatch):
    workspace = Workspace(
        name="Saleshandy Demo",
        product_url="https://my.saleshandy.com/demo",
        allowed_domains="my.saleshandy.com",
        browser_auth_mode="none",
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    demo_session = DemoSession(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        buyer_name="Jamie",
    )
    session.add(demo_session)
    session.commit()
    session.refresh(demo_session)

    dummy_driver = object()
    media = _RetryingMediaPublisher()
    requested_roles: list[str] = []

    async def fake_start_browser_session(db, current_session):
        current_session.browser_session_id = current_session.id
        db.add(current_session)
        db.commit()
        return "no-auth"

    def fake_get_active_driver(session_id: str):
        return dummy_driver

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        requested_roles.append(role)
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=room_name or f"demo-{session_id}",
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    monkeypatch.setattr("app.live.runtime.start_browser_session", fake_start_browser_session)
    monkeypatch.setattr("app.live.runtime.get_active_driver", fake_get_active_driver)
    monkeypatch.setattr("app.live.runtime.create_livekit_participant", fake_contract)

    bind = getattr(session.get_bind(), "engine", session.get_bind())
    runtime = LiveDemoRuntime(
        demo_session.id,
        workspace.id,
        db_factory=lambda: Session(bind),
        media_publisher=media,
    )

    result = await runtime.start(session, demo_session, workspace)

    assert result.buyer_contract.room_name == f"demo-{demo_session.id}"
    assert requested_roles[:3] == ["buyer", "agent", "browser"]

    await asyncio.wait_for(media.ready.wait(), timeout=5)
    assert media.start_attempts >= 2

    await runtime.stop()
    assert media.stop_called is True


@pytest.mark.asyncio
async def test_live_runtime_speak_does_not_raise_when_media_fails():
    runtime = LiveDemoRuntime("session-1", "workspace-1", media_publisher=_ExplodingMediaPublisher())
    runtime._media_ready.set()

    await runtime.speak_agent_message("Hello there")


@pytest.mark.asyncio
async def test_live_runtime_speaks_intro_once_requested_after_media_is_ready(session, monkeypatch):
    workspace = Workspace(
        name="Zoho Invoice Demo",
        product_url="https://www.zoho.com/in/invoice/invoicing-software-demo/",
        allowed_domains="www.zoho.com",
        browser_auth_mode="none",
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    demo_session = DemoSession(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        buyer_name="Riley",
        browser_session_id="session-browser-1",
    )
    session.add(demo_session)
    session.commit()
    session.refresh(demo_session)

    media = _RetryingMediaPublisher()

    def fake_get_active_driver(session_id: str):
        return object()

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=room_name or f"demo-{session_id}",
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    monkeypatch.setattr("app.live.runtime.get_active_driver", fake_get_active_driver)
    monkeypatch.setattr("app.live.runtime.create_livekit_participant", fake_contract)

    bind = getattr(session.get_bind(), "engine", session.get_bind())
    runtime = LiveDemoRuntime(
        demo_session.id,
        workspace.id,
        db_factory=lambda: Session(bind),
        media_publisher=media,
    )

    await runtime.start(session, demo_session, workspace)
    await asyncio.wait_for(media.ready.wait(), timeout=5)
    await runtime.speak_intro_greeting()

    assert media.spoken == [
        "Welcome Riley. I'll tailor this Zoho Invoice Demo walkthrough to your evaluation goals."
    ]

    await runtime.stop()


@pytest.mark.asyncio
async def test_live_runtime_executes_stagehand_action_before_recipe_fallback(session, monkeypatch):
    workspace = Workspace(
        name="Public Demo",
        product_url="https://public.example.com/demo",
        allowed_domains="public.example.com",
        browser_auth_mode="none",
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    demo_session = DemoSession(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        buyer_name="Riley",
        browser_session_id="session-browser-2",
    )
    session.add(demo_session)
    session.commit()
    session.refresh(demo_session)

    recipe_calls: list[str] = []

    async def fake_execute_action(db, session_id, action, target=None, value=None):
        return ActionResult(
            success=True,
            action_type="ai_act",
            target=target,
            narration="Opened the dashboard",
            page_title="Dashboard",
            page_url="https://public.example.com/dashboard",
        )

    async def fake_execute_recipe_step(db, session_id, step):
        recipe_calls.append(step.get("action", ""))
        return ActionResult(success=True, action_type=step.get("action", ""))

    monkeypatch.setattr("app.live.runtime.execute_action", fake_execute_action)
    monkeypatch.setattr("app.live.runtime.execute_recipe_step", fake_execute_recipe_step)

    captured_events: list[dict[str, object]] = []
    runtime = LiveDemoRuntime(
        demo_session.id,
        workspace.id,
        db_factory=lambda: Session(getattr(session.get_bind(), "engine", session.get_bind())),
        media_publisher=_RetryingMediaPublisher(),
        event_sink=lambda event: captured_events.append(event),
    )

    from app.models.recipe import DemoRecipe

    await runtime.perform_browser_instruction(
        "Show the dashboard",
        fallback_recipe=DemoRecipe(
            workspace_id=workspace.id,
            name="Dashboard Recipe",
            steps_json='[{"action":"navigate","target":"https://public.example.com/dashboard"}]',
        ),
        focus="Dashboard",
    )

    assert any(event["type"] == "browser_action_planned" for event in captured_events)
    assert any(event["type"] == "browser_action_result" and event["success"] is True for event in captured_events)
    assert recipe_calls == []


@pytest.mark.asyncio
async def test_live_runtime_emits_pointer_and_verified_browser_events(session, monkeypatch):
    workspace = Workspace(
        name="Public Demo",
        product_url="https://public.example.com/demo",
        allowed_domains="public.example.com",
        browser_auth_mode="none",
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    demo_session = DemoSession(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        buyer_name="Riley",
        browser_session_id="session-browser-telemetry",
    )
    session.add(demo_session)
    session.commit()
    session.refresh(demo_session)

    async def fake_execute_action(db, session_id, action, target=None, value=None):
        return ActionResult(
            success=True,
            action_type="ai_act",
            target=target,
            narration="Opened the dashboard",
            page_title="Dashboard",
            page_url="https://public.example.com/dashboard",
            telemetry={"kind": "click", "selector": "#dashboard", "x": 240, "y": 160, "label": "Dashboard"},
        )

    monkeypatch.setattr("app.live.runtime.execute_action", fake_execute_action)

    captured_events: list[dict[str, object]] = []
    runtime = LiveDemoRuntime(
        demo_session.id,
        workspace.id,
        db_factory=lambda: Session(getattr(session.get_bind(), "engine", session.get_bind())),
        media_publisher=_RetryingMediaPublisher(),
        event_sink=lambda event: captured_events.append(event),
    )

    await runtime.perform_browser_instruction("Show the dashboard", focus="Dashboard")

    assert any(event["type"] == "browser_pointer_move" for event in captured_events)
    assert any(event["type"] == "browser_click" for event in captured_events)
    assert any(event["type"] == "browser_action_verified" for event in captured_events)


@pytest.mark.asyncio
async def test_live_runtime_buyer_activity_cancels_inflight_action_and_recipe(monkeypatch):
    captured_events: list[dict[str, object]] = []
    runtime = LiveDemoRuntime(
        "session-activity",
        "workspace-activity",
        media_publisher=_RetryingMediaPublisher(),
        event_sink=lambda event: captured_events.append(event),
    )

    async def fake_update_session_state(*args, **kwargs):
        return None

    action_cancelled = asyncio.Event()
    recipe_cancelled = asyncio.Event()

    async def long_action():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            action_cancelled.set()
            raise

    async def long_recipe():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            recipe_cancelled.set()
            raise

    monkeypatch.setattr(runtime, "_update_session_state", fake_update_session_state)
    runtime._action_task = asyncio.create_task(long_action())
    runtime._recipe_task = asyncio.create_task(long_recipe())
    await asyncio.sleep(0)

    await runtime.handle_buyer_activity()
    await asyncio.sleep(0)

    assert action_cancelled.is_set()
    assert recipe_cancelled.is_set()
    assert any(event["type"] == "voice_state" and event["state"] == "listening" for event in captured_events)


@pytest.mark.asyncio
async def test_live_runtime_replaces_stale_turn_task(monkeypatch):
    runtime = LiveDemoRuntime("session-turn", "workspace-turn", media_publisher=_RetryingMediaPublisher())
    cancellations: list[str] = []
    started: list[str] = []

    async def fake_interrupt():
        return None

    async def fake_process(self, turn_generation: int, content: str):
        started.append(content)
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancellations.append(content)
            raise

    monkeypatch.setattr(runtime, "_interrupt_for_buyer_turn", fake_interrupt)
    monkeypatch.setattr(runtime, "_process_buyer_turn", types.MethodType(fake_process, runtime))

    await runtime.handle_buyer_transcript("first request")
    first_task = runtime._turn_task
    await asyncio.sleep(0)
    await runtime.handle_buyer_transcript("second request")
    await asyncio.sleep(0)

    assert first_task is not None
    assert cancellations == ["first request"]
    assert started == ["first request", "second request"]
    assert runtime._turn_generation == 2

    runtime._cancel_task(runtime._turn_task)
