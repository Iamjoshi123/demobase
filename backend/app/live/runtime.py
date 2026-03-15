"""Live demo runtime orchestration for browser, events, and media."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlmodel import Session

from app.browser.executor import (
    close_browser_session,
    execute_action,
    execute_recipe_step,
    get_active_driver,
    start_browser_session,
)
from app.config import settings
from app.database import engine
from app.live.events import event_broker
from app.live.media import MediaPublisher, create_media_publisher
from app.live.room import LiveKitParticipantContract, create_livekit_participant
from app.models.recipe import DemoRecipe
from app.models.session import DemoSession, SessionMessage
from app.models.workspace import Workspace
from app.services.planner import plan_response
from app.v2.language import build_greeting_text, meeting_language
from app.v2.models import MeetingSessionV2

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]
EventSink = Callable[[dict[str, object]], Awaitable[None] | None]


@dataclass
class LiveStartResult:
    buyer_contract: LiveKitParticipantContract
    capabilities: dict[str, object]


@dataclass(frozen=True)
class RecipeSnapshot:
    id: str
    workspace_id: str
    name: str
    steps_json: str
    description: str | None = None


def _session_factory() -> Session:
    return Session(engine)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _event(event_type: str, **payload: object) -> dict[str, object]:
    return {
        "type": event_type,
        "timestamp": _utc_now().isoformat(),
        **payload,
    }


def _snapshot_recipe(recipe: DemoRecipe | None) -> RecipeSnapshot | None:
    if recipe is None:
        return None
    return RecipeSnapshot(
        id=recipe.id,
        workspace_id=recipe.workspace_id,
        name=recipe.name,
        steps_json=recipe.steps_json,
        description=recipe.description,
    )


class LiveDemoRuntime:
    def __init__(
        self,
        session_id: str,
        workspace_id: str,
        *,
        db_factory: SessionFactory = _session_factory,
        media_publisher: Optional[MediaPublisher] = None,
        event_sink: Optional[EventSink] = None,
        meeting_id: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        self.workspace_id = workspace_id
        self._db_factory = db_factory
        self._media = media_publisher or create_media_publisher()
        self._event_sink = event_sink
        self._meeting_id = meeting_id
        self._pause_gate = asyncio.Event()
        self._pause_gate.set()
        self._recipe_task: Optional[asyncio.Task[None]] = None
        self._active_recipe_id: Optional[str] = None
        self._active_recipe_name: Optional[str] = None
        self._recipe_steps: list[dict] = []
        self._current_step_index = 0
        self._single_step_budget = 0
        self._room_name: Optional[str] = None
        self._media_task: Optional[asyncio.Task[None]] = None
        self._media_ready = asyncio.Event()
        self._interaction_ready = asyncio.Event()
        self._media_error: Optional[str] = None
        self._greeting_text: Optional[str] = None
        self._greeting_sent = False
        self._greeting_requested = False
        self._startup_states: set[str] = set()
        self._turn_task: Optional[asyncio.Task[None]] = None
        self._action_task: Optional[asyncio.Task[None]] = None
        self._turn_generation = 0

    async def start(self, db: Session, session: DemoSession, workspace: Workspace) -> LiveStartResult:
        if not session.browser_session_id or get_active_driver(session.id) is None:
            browser_result = await start_browser_session(db, session)
            if browser_result is None:
                raise RuntimeError("Could not start browser session for live demo")

        buyer_contract = create_livekit_participant(
            session.id,
            role="buyer",
            name=session.buyer_name or "Demo Buyer",
            can_publish=True,
            can_subscribe=True,
        )
        agent_contract = create_livekit_participant(
            session.id,
            role="agent",
            name="Demo Agent",
            room_name=buyer_contract.room_name,
            identity=f"agent-voice-{session.id}",
            can_publish=True,
            can_subscribe=True,
        )
        browser_contract = create_livekit_participant(
            session.id,
            role="browser",
            name="Demo Browser",
            room_name=buyer_contract.room_name,
            identity=f"agent-browser-{session.id}",
            can_publish=True,
            can_subscribe=False,
        )

        self._room_name = buyer_contract.room_name
        driver = get_active_driver(session.id)
        if driver is None:
            raise RuntimeError("Browser driver is not available for live demo")

        preferred_language = "en"
        if self._meeting_id:
            meeting = db.get(MeetingSessionV2, self._meeting_id)
            if meeting is not None:
                preferred_language = meeting_language(meeting)
        self._greeting_text = build_greeting_text(
            buyer_name=session.buyer_name,
            workspace_name=workspace.name,
            language_code=preferred_language,
        )
        self._media_ready.clear()
        self._interaction_ready.clear()
        self._startup_states.clear()
        self._greeting_sent = False
        self._greeting_requested = False
        self._launch_media_start(driver, agent_contract, browser_contract)

        session.mode = "live"
        session.live_status = "live"
        session.live_room_name = buyer_contract.room_name
        session.live_participant_identity = buyer_contract.participant_identity
        db.add(session)
        db.commit()
        db.refresh(session)

        await self._publish_event(
            _event(
                "status",
                live_status=session.live_status,
                room_name=session.live_room_name,
                current_step_index=session.current_step_index,
            )
        )

        return LiveStartResult(
            buyer_contract=buyer_contract,
            capabilities={
                "voice": settings.enable_voice,
                "video": True,
                "mock_media": self._media.__class__.__name__ == "NullMediaPublisher",
                "media_pending": not self._media_ready.is_set(),
                "assist_controls": ["pause", "resume", "next-step", "restart"],
                "text_fallback": True,
            },
        )

    async def speak_agent_message(self, text: str) -> None:
        if not self._media_ready.is_set():
            logger.info("Skipping agent speech because live media is not ready for session %s", self.session_id)
            return
        try:
            await self._media.speak(text)
        except Exception as exc:
            logger.exception("Agent speech failed for session %s", self.session_id)
            self._media_error = str(exc)
            await self._publish_event(
                _event(
                    "runtime_error",
                    detail=f"Agent audio failed: {exc}",
                    action_type="speak",
                )
            )

    async def speak_intro_greeting(self) -> None:
        if self._greeting_sent or not self._greeting_text:
            return
        try:
            await asyncio.wait_for(self._interaction_ready.wait(), timeout=12)
        except asyncio.TimeoutError:
            logger.warning("Skipping intro greeting because live media did not become ready for session %s", self.session_id)
            return
        await self.speak_agent_message(self._greeting_text)
        self._greeting_sent = True

    async def request_intro_greeting(self) -> None:
        if self._greeting_requested:
            return
        self._greeting_requested = True
        await self.speak_intro_greeting()

    async def queue_recipe(self, recipe: DemoRecipe | RecipeSnapshot) -> None:
        recipe_snapshot = _snapshot_recipe(recipe) if isinstance(recipe, DemoRecipe) else recipe
        if recipe_snapshot is None:
            return
        if self._recipe_task:
            self._recipe_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._recipe_task

        self._active_recipe_id = recipe_snapshot.id
        self._active_recipe_name = recipe_snapshot.name
        self._recipe_steps = json.loads(recipe_snapshot.steps_json)
        self._current_step_index = 0
        self._single_step_budget = 0
        self._pause_gate.set()
        self._recipe_task = asyncio.create_task(self._run_recipe_loop())

        await self._update_session_state(
            live_status="live",
            active_recipe_id=recipe_snapshot.id,
            current_step_index=0,
        )
        await self._publish_event(
            _event(
                "recipe_started",
                recipe_id=recipe_snapshot.id,
                recipe_name=recipe_snapshot.name,
                total_steps=len(self._recipe_steps),
            )
        )

    async def perform_browser_instruction(
        self,
        instruction: str,
        *,
        fallback_recipe: Optional[DemoRecipe | RecipeSnapshot] = None,
        focus: Optional[str] = None,
    ) -> None:
        if not instruction.strip():
            return
        recipe_snapshot = _snapshot_recipe(fallback_recipe) if isinstance(fallback_recipe, DemoRecipe) else fallback_recipe

        if self._recipe_task:
            self._recipe_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._recipe_task
            self._recipe_task = None

        self._active_recipe_id = None
        self._active_recipe_name = None
        self._recipe_steps = []
        self._current_step_index = 0
        self._single_step_budget = 0
        self._pause_gate.set()

        await self._update_session_state(live_status="live", active_recipe_id=None, current_step_index=0)
        await self._publish_event(
            _event(
                "browser_action_planned",
                instruction=instruction,
                focus=focus or instruction,
                action_strategy="stagehand",
                fallback_recipe_id=recipe_snapshot.id if recipe_snapshot else None,
                fallback_recipe_name=recipe_snapshot.name if recipe_snapshot else None,
            )
        )

        with self._db_factory() as db:
            result = await execute_action(db, self.session_id, "ai_act", instruction)

        await self._publish_browser_action_events(
            result,
            focus=focus or getattr(result, "page_title", None) or instruction,
            instruction=instruction,
            action_strategy="stagehand",
            fallback_recipe_id=recipe_snapshot.id if recipe_snapshot else None,
            fallback_recipe_name=recipe_snapshot.name if recipe_snapshot else None,
        )

        if result.success:
            await self._publish_event(
                _event(
                    "browser_action_result",
                    success=True,
                    instruction=instruction,
                    focus=focus or result.page_title or instruction,
                    action_strategy="stagehand",
                    narration=result.narration,
                    page_url=result.page_url,
                    page_title=result.page_title,
                )
            )
            return

        await self._publish_event(
            _event(
                "browser_action_result",
                success=False,
                instruction=instruction,
                focus=focus or instruction,
                action_strategy="stagehand",
                narration=result.narration,
                error=result.error,
                fallback_recipe_id=recipe_snapshot.id if recipe_snapshot else None,
                fallback_recipe_name=recipe_snapshot.name if recipe_snapshot else None,
            )
        )
        if recipe_snapshot is not None:
            await self._publish_event(
                _event(
                    "browser_action_fallback",
                    instruction=instruction,
                    detail="Direct browser action failed. Falling back to the structured walkthrough.",
                    fallback_recipe_id=recipe_snapshot.id,
                    fallback_recipe_name=recipe_snapshot.name,
                )
            )
            await self.queue_recipe(recipe_snapshot)
            return

        await self._publish_event(
            _event(
                "runtime_error",
                detail=result.error or "Direct browser action failed",
                action_type="ai_act",
                instruction=instruction,
            )
        )

    async def pause(self) -> dict[str, object]:
        self._pause_gate.clear()
        await self._update_session_state(live_status="paused")
        payload = {
            "session_id": self.session_id,
            "live_status": "paused",
            "active_recipe_id": self._active_recipe_id,
            "current_step_index": self._current_step_index,
            "detail": "Live demo paused",
        }
        await self._publish_event(_event("status", **payload))
        return payload

    async def resume(self) -> dict[str, object]:
        self._single_step_budget = 0
        self._pause_gate.set()
        await self._update_session_state(live_status="live")
        payload = {
            "session_id": self.session_id,
            "live_status": "live",
            "active_recipe_id": self._active_recipe_id,
            "current_step_index": self._current_step_index,
            "detail": "Live demo resumed",
        }
        await self._publish_event(_event("status", **payload))
        return payload

    async def next_step(self) -> dict[str, object]:
        self._single_step_budget = 1
        self._pause_gate.set()
        payload = {
            "session_id": self.session_id,
            "live_status": "live",
            "active_recipe_id": self._active_recipe_id,
            "current_step_index": self._current_step_index,
            "detail": "Advancing one recipe step",
        }
        await self._publish_event(_event("control", control="next-step", **payload))
        return payload

    async def restart(self) -> dict[str, object]:
        if self._recipe_task:
            self._recipe_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._recipe_task

        self._current_step_index = 0
        self._single_step_budget = 0
        self._pause_gate.set()

        if self._active_recipe_id and self._recipe_steps:
            self._recipe_task = asyncio.create_task(self._run_recipe_loop())

        await self._update_session_state(live_status="live", current_step_index=0)
        payload = {
            "session_id": self.session_id,
            "live_status": "live",
            "active_recipe_id": self._active_recipe_id,
            "current_step_index": self._current_step_index,
            "detail": "Restarted live demo recipe",
        }
        await self._publish_event(_event("control", control="restart", **payload))
        return payload

    async def stop(self) -> None:
        self._cancel_task(self._turn_task)
        self._cancel_task(self._action_task)
        if self._media_task:
            self._media_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._media_task
            self._media_task = None

        if self._recipe_task:
            self._recipe_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._recipe_task
            self._recipe_task = None

        await self._media.stop()
        with self._db_factory() as db:
            await close_browser_session(db, self.session_id)
            current = db.get(DemoSession, self.session_id)
            if current:
                current.live_status = "ended"
                current.live_room_name = self._room_name
                db.add(current)
                db.commit()

        await self._publish_event(_event("session_ended", session_id=self.session_id))

    async def handle_buyer_transcript(self, content: str) -> None:
        if not content.strip():
            return
        await self._interrupt_for_buyer_turn()
        self._turn_generation += 1
        turn_generation = self._turn_generation
        self._cancel_task(self._turn_task)
        self._turn_task = asyncio.create_task(self._process_buyer_turn(turn_generation, content.strip()))
        self._turn_task.add_done_callback(self._clear_turn_task)

    async def _process_buyer_turn(self, turn_generation: int, content: str) -> None:
        try:
            with self._db_factory() as db:
                current = db.get(DemoSession, self.session_id)
                if current is None:
                    return

                user_msg = SessionMessage(
                    session_id=self.session_id,
                    role="user",
                    content=content,
                    message_type="voice_transcript",
                )
                db.add(user_msg)
                db.commit()
                db.refresh(user_msg)
                await self._publish_event(
                    _event("transcript", role="user", content=content, message_type="voice_transcript")
                )
                await self._publish_event(
                    _event("voice_state", state="thinking", detail="Agent is processing your question.")
                )

                if self._meeting_id:
                    from app.v2.models import MeetingSessionV2
                    from app.v2.orchestrator import MeetingOrchestrator

                    meeting = db.get(MeetingSessionV2, self._meeting_id)
                    if meeting is not None:
                        turn = await MeetingOrchestrator().handle_turn(db, meeting, content, realtime=True)
                        recipe = _snapshot_recipe(db.get(DemoRecipe, turn.recipe_id) if turn.recipe_id else None)
                        agent_msg = SessionMessage(
                            session_id=self.session_id,
                            role="agent",
                            content=turn.response_text,
                            message_type="voice_transcript",
                            planner_decision=turn.action_strategy,
                            metadata_json=json.dumps(
                                {
                                    "recipe_id": turn.recipe_id,
                                    "citations": turn.citations,
                                    "policy_decision": turn.policy_decision,
                                    "browser_instruction": turn.browser_instruction,
                                    "action_strategy": turn.action_strategy,
                                    "next_actions": turn.next_actions,
                                }
                            ),
                        )
                        db.add(agent_msg)
                        db.commit()
                        db.refresh(agent_msg)
                        planner_payload = {
                            "decision": turn.action_strategy,
                            "response_text": turn.response_text,
                            "recipe": recipe,
                            "next_actions": turn.next_actions,
                            "browser_instruction": turn.browser_instruction,
                            "policy_decision": turn.policy_decision,
                        }
                    else:
                        planner_payload = None
                else:
                    planner_payload = None

                if planner_payload is None:
                    plan = await plan_response(db, current, content)
                    agent_msg = SessionMessage(
                        session_id=self.session_id,
                        role="agent",
                        content=plan.response_text,
                        message_type="voice_transcript",
                        planner_decision=plan.decision,
                        metadata_json=json.dumps(
                            {
                                "recipe_id": plan.recipe_id,
                                "citations": plan.citations,
                                "policy_decision": plan.policy_decision.decision if plan.policy_decision else None,
                            }
                        ),
                    )
                    db.add(agent_msg)
                    db.commit()
                    db.refresh(agent_msg)
                    recipe = _snapshot_recipe(db.get(DemoRecipe, plan.recipe_id) if plan.recipe_id else None)
                    planner_payload = {
                        "decision": plan.decision,
                        "response_text": plan.response_text,
                        "recipe": recipe,
                        "next_actions": [],
                        "browser_instruction": None,
                        "policy_decision": plan.policy_decision.decision if plan.policy_decision else None,
                    }

            if turn_generation != self._turn_generation:
                logger.info("Discarding stale buyer turn for session %s", self.session_id)
                return

            await self._publish_event(
                _event(
                    "transcript",
                    role="agent",
                    content=planner_payload["response_text"],
                    message_type="voice_transcript",
                    planner_decision=planner_payload["decision"],
                    next_actions=planner_payload["next_actions"],
                    metadata={
                        "browser_instruction": planner_payload["browser_instruction"],
                        "policy_decision": planner_payload["policy_decision"],
                    },
                )
            )
            recipe = planner_payload["recipe"]
            browser_instruction = planner_payload["browser_instruction"]
            self._action_task = None
            action_task: Optional[asyncio.Task[None]] = None
            if browser_instruction:
                action_task = asyncio.create_task(
                    self.perform_browser_instruction(browser_instruction, fallback_recipe=recipe)
                )
                self._action_task = action_task
                action_task.add_done_callback(self._clear_action_task)
            elif planner_payload["decision"] in {"answer_and_demo", "recipe_fallback", "recipe_only"} and recipe is not None:
                action_task = asyncio.create_task(self.queue_recipe(recipe))
                self._action_task = action_task
                action_task.add_done_callback(self._clear_action_task)

            speech_task = asyncio.create_task(self.speak_agent_message(planner_payload["response_text"]))
            await self._publish_event(
                _event("voice_state", state="speaking", detail="Agent is responding.")
            )
            tasks = [speech_task]
            if action_task is not None:
                tasks.append(action_task)
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                self._cancel_task(speech_task)
                if action_task is not None:
                    self._cancel_task(action_task)
                raise
            finally:
                if self._action_task is action_task:
                    self._action_task = None

            if turn_generation == self._turn_generation:
                await self._publish_event(
                    _event("voice_state", state="idle", detail="Agent is ready for the next question.")
                )
        except asyncio.CancelledError:
            logger.info("Cancelled buyer turn for session %s", self.session_id)
            raise
        except Exception as exc:
            logger.exception("Live buyer turn failed for session %s", self.session_id)
            await self._publish_event(
                _event(
                    "runtime_error",
                    detail=f"Live turn failed: {exc}",
                    action_type="voice_turn",
                )
            )

    async def _run_recipe_loop(self) -> None:
        while self._current_step_index < len(self._recipe_steps):
            await self._pause_gate.wait()
            step = self._recipe_steps[self._current_step_index]

            with self._db_factory() as db:
                result = await execute_recipe_step(db, self.session_id, step)
                self._current_step_index += 1
                current = db.get(DemoSession, self.session_id)
                if current:
                    current.active_recipe_id = self._active_recipe_id
                    current.current_step_index = self._current_step_index
                    current.live_status = "live"
                    db.add(current)
                    db.commit()

            await self._publish_event(
                _event(
                    "recipe_step",
                    recipe_id=self._active_recipe_id,
                    recipe_name=self._active_recipe_name,
                    step_index=self._current_step_index,
                    action_type=result.action_type,
                    success=result.success,
                    narration=result.narration,
                    error=result.error,
                    page_url=result.page_url,
                    page_title=result.page_title,
                )
            )
            await self._publish_browser_action_events(
                result,
                focus=result.page_title or self._active_recipe_name or step.get("target"),
                instruction=str(step.get("target") or step.get("action") or ""),
                action_strategy="recipe",
                recipe_id=self._active_recipe_id,
                recipe_name=self._active_recipe_name,
                step_index=self._current_step_index,
            )

            if not result.success:
                await self._publish_event(
                    _event(
                        "runtime_error",
                        detail=result.error or "Recipe step failed",
                        action_type=result.action_type,
                    )
                )

            if self._single_step_budget > 0:
                self._single_step_budget -= 1
                if self._single_step_budget == 0:
                    self._pause_gate.clear()
                    await self._update_session_state(live_status="paused")
                    await self._publish_event(
                        _event(
                            "status",
                            session_id=self.session_id,
                            live_status="paused",
                            active_recipe_id=self._active_recipe_id,
                            current_step_index=self._current_step_index,
                            detail="Paused after single step",
                        )
                    )

        await self._update_session_state(
            live_status="live",
            active_recipe_id=self._active_recipe_id,
            current_step_index=self._current_step_index,
        )
        await self._publish_event(
            _event(
                "recipe_completed",
                recipe_id=self._active_recipe_id,
                recipe_name=self._active_recipe_name,
                total_steps=self._current_step_index,
            )
        )

    async def _publish_event(self, event: dict[str, object]) -> None:
        await event_broker.publish(self.session_id, event)
        if self._event_sink is None:
            return
        result = self._event_sink(event)
        if asyncio.iscoroutine(result):
            await result

    async def _update_session_state(
        self,
        *,
        live_status: Optional[str] = None,
        active_recipe_id: Optional[str] = None,
        current_step_index: Optional[int] = None,
    ) -> None:
        with self._db_factory() as db:
            current = db.get(DemoSession, self.session_id)
            if current is None:
                return
            if live_status is not None:
                current.live_status = live_status
            if active_recipe_id is not None:
                current.active_recipe_id = active_recipe_id
            if current_step_index is not None:
                current.current_step_index = current_step_index
            if self._room_name:
                current.live_room_name = self._room_name
            db.add(current)
            db.commit()

    def _launch_media_start(
        self,
        driver: object,
        agent_contract: LiveKitParticipantContract,
        browser_contract: LiveKitParticipantContract,
    ) -> None:
        if self._media_task and not self._media_task.done():
            return
        self._media_task = asyncio.create_task(self._start_media_with_retry(driver, agent_contract, browser_contract))

    async def _start_media_with_retry(
        self,
        driver: object,
        agent_contract: LiveKitParticipantContract,
        browser_contract: LiveKitParticipantContract,
    ) -> None:
        delays = [0.0, 1.0, 2.0, 4.0]
        last_error: Optional[Exception] = None

        for attempt, delay_seconds in enumerate(delays, start=1):
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            attempt_contract = agent_contract
            attempt_browser_contract = browser_contract
            if attempt > 1:
                attempt_contract = create_livekit_participant(
                    self.session_id,
                    role="agent",
                    name=agent_contract.participant_name,
                    room_name=agent_contract.room_name,
                    identity=f"agent-voice-{self.session_id}-{uuid.uuid4().hex[:8]}",
                    can_publish=True,
                    can_subscribe=True,
                )
                attempt_browser_contract = create_livekit_participant(
                    self.session_id,
                    role="browser",
                    name=browser_contract.participant_name,
                    room_name=browser_contract.room_name,
                    identity=f"agent-browser-{self.session_id}-{uuid.uuid4().hex[:8]}",
                    can_publish=True,
                    can_subscribe=False,
                )
                logger.info(
                    "Retrying live media attach for session %s with fresh identities voice=%s browser=%s",
                    self.session_id,
                    attempt_contract.participant_identity,
                    attempt_browser_contract.participant_identity,
                )
            try:
                await self._media.start(
                    driver,
                    attempt_contract,
                    browser_contract=attempt_browser_contract,
                    on_transcript=self.handle_buyer_transcript,
                    on_speech_activity=self.handle_buyer_activity,
                    on_startup_state=self._handle_startup_state,
                )
                self._media_ready.set()
                self._media_error = None
                if self._greeting_text and not self._greeting_requested:
                    asyncio.create_task(self.request_intro_greeting())
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                self._media_error = str(exc)
                logger.warning(
                    "Live media attach attempt %s failed for session %s: %s",
                    attempt,
                    self.session_id,
                    exc,
                )

        detail = f"Live media failed to attach: {last_error}" if last_error else "Live media failed to attach"
        await self._publish_event(
            _event(
                "startup_state",
                state="failed",
                detail=detail,
            )
        )
        await self._publish_event(
            _event(
                "runtime_error",
                detail=detail,
                action_type="media_start",
            )
        )
        await self._publish_event(
            _event(
                "browser_stage_state",
                state="errored",
                detail=detail,
            )
        )

    async def _handle_startup_state(self, state: str, detail: str | None) -> None:
        self._startup_states.add(state)
        await self._publish_event(_event("startup_state", state=state, detail=detail))

        if state == "browser_publisher_ready":
            await self._publish_event(
                _event(
                    "browser_stage_state",
                    state="attaching",
                    detail="Browser track published. Waiting for live frames on the buyer page.",
                )
            )

        required = {"agent_audio_ready", "buyer_audio_ready", "browser_publisher_ready"}
        if not self._interaction_ready.is_set() and required.issubset(self._startup_states):
            self._interaction_ready.set()
            await self._publish_event(
                _event(
                    "startup_state",
                    state="interaction_ready",
                    detail="Voice and browser are ready for the live walkthrough.",
                )
            )
            await self._publish_event(
                _event(
                    "status",
                    session_id=self.session_id,
                    live_status="live",
                    media_status="ready",
                    active_recipe_id=self._active_recipe_id,
                    current_step_index=self._current_step_index,
                )
            )

    async def handle_buyer_activity(self) -> None:
        self._cancel_task(self._action_task)
        if self._recipe_task and not self._recipe_task.done():
            self._recipe_task.cancel()
            self._pause_gate.clear()
            await self._update_session_state(live_status="live", current_step_index=self._current_step_index)
        await self._publish_event(
            _event("voice_state", state="listening", detail="Buyer is speaking.")
        )

    async def _interrupt_for_buyer_turn(self) -> None:
        await self.handle_buyer_activity()
        await self._media.interrupt_speech()

    def _cancel_task(self, task: Optional[asyncio.Task[None]]) -> None:
        if task is not None and not task.done():
            task.cancel()

    def _clear_turn_task(self, task: asyncio.Task[None]) -> None:
        if self._turn_task is task:
            self._turn_task = None

    def _clear_action_task(self, task: asyncio.Task[None]) -> None:
        if self._action_task is task:
            self._action_task = None

    async def _publish_browser_action_events(
        self,
        result: object,
        *,
        focus: str | None,
        instruction: str,
        action_strategy: str,
        fallback_recipe_id: str | None = None,
        fallback_recipe_name: str | None = None,
        recipe_id: str | None = None,
        recipe_name: str | None = None,
        step_index: int | None = None,
    ) -> None:
        telemetry = getattr(result, "telemetry", None)
        if isinstance(telemetry, dict) and telemetry:
            await self._publish_browser_pointer_event(telemetry)

        verification_event = "browser_action_verified" if getattr(result, "success", False) else "browser_action_failed"
        await self._publish_event(
            _event(
                verification_event,
                action_type=getattr(result, "action_type", None),
                instruction=instruction,
                focus=focus,
                action_strategy=action_strategy,
                success=getattr(result, "success", False),
                narration=getattr(result, "narration", None),
                error=getattr(result, "error", None),
                page_url=getattr(result, "page_url", None),
                page_title=getattr(result, "page_title", None),
                fallback_recipe_id=fallback_recipe_id,
                fallback_recipe_name=fallback_recipe_name,
                recipe_id=recipe_id,
                recipe_name=recipe_name,
                step_index=step_index,
                telemetry=telemetry if isinstance(telemetry, dict) else None,
            )
        )

    async def _publish_browser_pointer_event(self, telemetry: dict[str, object]) -> None:
        payload = {
            "x": float(telemetry["x"]) if isinstance(telemetry.get("x"), (int, float)) else None,
            "y": float(telemetry["y"]) if isinstance(telemetry.get("y"), (int, float)) else None,
            "width": float(telemetry["width"]) if isinstance(telemetry.get("width"), (int, float)) else None,
            "height": float(telemetry["height"]) if isinstance(telemetry.get("height"), (int, float)) else None,
            "selector": telemetry.get("selector"),
            "label": telemetry.get("label"),
        }
        await self._publish_event(_event("browser_pointer_move", **payload))

        kind = str(telemetry.get("kind") or "").lower()
        if kind == "scroll":
            await self._publish_event(
                _event(
                    "browser_scroll",
                    **payload,
                    direction=telemetry.get("direction"),
                    delta_y=telemetry.get("delta_y"),
                )
            )
            return
        if kind == "type":
            await self._publish_event(
                _event(
                    "browser_type",
                    **payload,
                    typed_value=telemetry.get("typed_value"),
                )
            )
            return
        await self._publish_event(_event("browser_click", **payload))


class LiveRuntimeManager:
    def __init__(self) -> None:
        self._runtimes: dict[str, LiveDemoRuntime] = {}

    def get(self, session_id: str) -> Optional[LiveDemoRuntime]:
        return self._runtimes.get(session_id)

    def create(
        self,
        session_id: str,
        workspace_id: str,
        *,
        db_factory: SessionFactory = _session_factory,
        media_publisher: Optional[MediaPublisher] = None,
        event_sink: Optional[EventSink] = None,
        meeting_id: Optional[str] = None,
    ) -> LiveDemoRuntime:
        runtime = LiveDemoRuntime(
            session_id,
            workspace_id,
            db_factory=db_factory,
            media_publisher=media_publisher,
            event_sink=event_sink,
            meeting_id=meeting_id,
        )
        self._runtimes[session_id] = runtime
        return runtime

    async def stop(self, session_id: str) -> None:
        runtime = self._runtimes.pop(session_id, None)
        if runtime is not None:
            await runtime.stop()


runtime_manager = LiveRuntimeManager()
