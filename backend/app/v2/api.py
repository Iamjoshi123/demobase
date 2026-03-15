"""V2 meeting API for the rebuilt agentic demo experience."""

from __future__ import annotations

import logging
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.live.events import event_broker
from app.live.room import create_livekit_participant
from app.live.runtime import runtime_manager
from app.models.recipe import DemoRecipe
from app.models.session import DemoSession
from app.models.workspace import Workspace
from app.v2.bridge import build_runtime_event_sink, ensure_runtime_session, sync_meeting_from_runtime
from app.v2.models import (
    MeetingBrowserPlanRead,
    MeetingCreate,
    MeetingJoinRead,
    MeetingLiveControlRead,
    MeetingLiveStartRead,
    MeetingMessageCreate,
    MeetingMessageRead,
    MeetingMessageV2,
    MeetingPreferencesUpdate,
    MeetingRead,
    MeetingSessionV2,
    MeetingTurnRead,
)
from app.v2.language import build_greeting_text, sanitize_demo_language, update_meeting_language
from app.v2.orchestrator import MeetingOrchestrator, personalize_summary_payload
from app.v2.runtime import runtime_registry

router = APIRouter(prefix="/v2/meetings", tags=["meetings-v2"])
orchestrator = MeetingOrchestrator()
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_message(message: MeetingMessageV2) -> MeetingMessageRead:
    return MeetingMessageRead.model_validate(message)


def _event_ws_url(meeting_id: str) -> str:
    backend = settings.backend_url.rstrip("/")
    if backend.startswith("https://"):
        root = "wss://" + backend[len("https://"):]
    elif backend.startswith("http://"):
        root = "ws://" + backend[len("http://"):]
    elif backend.startswith("wss://") or backend.startswith("ws://"):
        root = backend
    else:
        root = f"ws://{backend}"
    return f"{root}/api/v2/meetings/{meeting_id}/events"


@router.post("", response_model=MeetingRead)
def create_meeting(data: MeetingCreate, db: Session = Depends(get_session)):
    workspace = db.exec(
        select(Workspace).where(
            Workspace.public_token == data.public_token,
            Workspace.is_active,
        )
    ).first()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Invalid meeting link")

    meeting = MeetingSessionV2(
        workspace_id=workspace.id,
        public_token=data.public_token,
        buyer_name=data.buyer_name,
        buyer_email=data.buyer_email,
        company_name=data.company_name,
        role_title=data.role_title,
        goal=data.goal,
    )
    update_meeting_language(meeting, data.language)
    meeting.personalization_json = personalize_summary_payload(meeting)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    welcome = MeetingMessageV2(
        session_id=meeting.id,
        role="agent",
        content=build_greeting_text(
            buyer_name=meeting.buyer_name,
            workspace_name=workspace.name,
            language_code=sanitize_demo_language(data.language),
        ),
        message_type="text",
        stage="intro",
        next_actions_json=json.dumps(["clarify_buyer_goal", "prepare_personalized_walkthrough"]),
        metadata_json=json.dumps({"workspace_name": workspace.name}),
    )
    db.add(welcome)
    db.commit()

    return meeting


@router.patch("/{meeting_id}/preferences", response_model=MeetingRead)
def update_meeting_preferences(meeting_id: str, data: MeetingPreferencesUpdate, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    update_meeting_language(meeting, data.language)
    meeting.updated_at = _utc_now()
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/{meeting_id}/messages", response_model=list[MeetingMessageRead])
def get_messages(meeting_id: str, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    messages = db.exec(
        select(MeetingMessageV2)
        .where(MeetingMessageV2.session_id == meeting_id)
        .order_by(MeetingMessageV2.created_at)
    ).all()
    return [_serialize_message(message) for message in messages]


@router.post("/{meeting_id}/messages", response_model=MeetingTurnRead)
async def send_message(
    meeting_id: str,
    data: MeetingMessageCreate,
    db: Session = Depends(get_session),
):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status != "active":
        raise HTTPException(status_code=400, detail="Meeting is not active")

    buyer_message = MeetingMessageV2(
        session_id=meeting.id,
        role="user",
        content=data.content,
        message_type=data.message_type,
        stage=meeting.stage,
        metadata_json=meeting.personalization_json,
    )
    db.add(buyer_message)
    db.commit()

    runtime_session = db.get(DemoSession, meeting.runtime_session_id) if meeting.runtime_session_id else None
    runtime = runtime_manager.get(runtime_session.id) if runtime_session else None

    try:
        turn = await orchestrator.handle_turn(db, meeting, data.content, realtime=runtime is not None)
    except Exception as exc:
        logger.exception("Meeting turn failed for %s", meeting.id)
        fallback = MeetingMessageV2(
            session_id=meeting.id,
            role="agent",
            content=(
                "The live demo runtime hit an error while preparing the response. "
                "Please retry the question or use the assist controls to continue the walkthrough."
            ),
            message_type="system",
            stage=meeting.stage,
            next_actions_json=json.dumps(["retry_question", "continue_walkthrough"]),
            metadata_json=json.dumps({"error": str(exc)}),
            created_at=_utc_now(),
        )
        db.add(fallback)
        db.commit()
        db.refresh(fallback)
        return MeetingTurnRead(
            message=_serialize_message(fallback),
            stage=meeting.stage,
            policy_decision="error",
            next_actions=["retry_question", "continue_walkthrough"],
            citations=[],
            recipe_id=None,
            browser_instruction=None,
            action_strategy="error",
            should_handoff=False,
        )
    now = _utc_now()
    meeting.stage = turn.stage
    meeting.current_focus = turn.focus
    meeting.updated_at = now
    db.add(meeting)

    agent_message = MeetingMessageV2(
        session_id=meeting.id,
        role="agent",
        content=turn.response_text,
        message_type="text",
        stage=turn.stage,
        next_actions_json=json.dumps(turn.next_actions),
        metadata_json=json.dumps(
            {
                "policy_decision": turn.policy_decision,
                "citations": turn.citations,
                "recipe_id": turn.recipe_id,
                "recipe_name": turn.recipe_name,
                "should_handoff": turn.should_handoff,
                **turn.metadata,
            }
        ),
        created_at=now,
    )
    db.add(agent_message)
    db.commit()
    db.refresh(agent_message)

    recipe = db.get(DemoRecipe, turn.recipe_id) if turn.recipe_id else None
    if runtime is not None:
        try:
            await runtime.speak_agent_message(turn.response_text)
        except Exception:
            logger.exception("Agent speech side effect failed for meeting %s", meeting.id)
        try:
            if turn.browser_instruction:
                await runtime.perform_browser_instruction(
                    turn.browser_instruction,
                    fallback_recipe=recipe,
                    focus=turn.focus,
                )
            elif recipe is not None:
                await runtime.queue_recipe(recipe)
        except Exception:
            logger.exception("Live browser side effect failed for meeting %s", meeting.id)

    if turn.recipe_id:
        meeting.active_recipe_id = turn.recipe_id
    if turn.stage == "demo":
        meeting.browser_status = "connected" if runtime is not None else "planned"
    db.add(meeting)
    db.commit()

    return MeetingTurnRead(
        message=_serialize_message(agent_message),
        stage=turn.stage,
        policy_decision=turn.policy_decision,
        next_actions=turn.next_actions,
        citations=turn.citations,
        recipe_id=turn.recipe_id,
        browser_instruction=turn.browser_instruction,
        action_strategy=turn.action_strategy,
        should_handoff=turn.should_handoff,
    )


@router.post("/{meeting_id}/join", response_model=MeetingJoinRead)
def join_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    state = runtime_registry.ensure(meeting.id, meeting.workspace_id)
    contract = create_livekit_participant(
        meeting.id,
        role="buyer",
        name=meeting.buyer_name or "Demo Buyer",
        room_name=f"meeting-{meeting.id}",
    )

    state.room_name = contract.room_name
    state.rtc_ready = True
    meeting.rtc_status = "ready"
    meeting.live_room_name = contract.room_name
    meeting.live_participant_identity = contract.participant_identity
    meeting.updated_at = _utc_now()
    db.add(meeting)
    db.commit()

    return MeetingJoinRead(
        room_name=contract.room_name,
        livekit_url=contract.livekit_url,
        participant_identity=contract.participant_identity,
        participant_name=contract.participant_name,
        participant_token=contract.token,
        event_ws_url=_event_ws_url(meeting.id),
        capabilities_json=json.dumps(
            {
                "voice": True,
                "browser_stream": True,
                "text_fallback": True,
                "assist_controls": ["pause", "resume", "next-step", "restart"],
            }
        ),
    )


@router.post("/{meeting_id}/browser-plan", response_model=MeetingBrowserPlanRead)
def plan_browser(meeting_id: str, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    workspace = db.get(Workspace, meeting.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    statement = (
        select(MeetingMessageV2)
        .where(MeetingMessageV2.session_id == meeting.id, MeetingMessageV2.role == "agent")
        .order_by(MeetingMessageV2.created_at.desc())
    )
    last_agent_message = db.exec(statement).first()
    metadata = json.loads(last_agent_message.metadata_json) if last_agent_message and last_agent_message.metadata_json else {}

    state = runtime_registry.ensure(meeting.id, meeting.workspace_id)
    state.browser_planned = True
    state.last_recipe_id = metadata.get("recipe_id")
    state.last_focus = meeting.current_focus

    meeting.browser_status = "planned"
    meeting.updated_at = _utc_now()
    db.add(meeting)
    db.commit()

    return MeetingBrowserPlanRead(
        session_id=meeting.id,
        product_url=workspace.product_url,
        allowed_domains=[item.strip() for item in workspace.allowed_domains.split(",") if item.strip()],
        suggested_recipe_id=metadata.get("recipe_id"),
        suggested_recipe_name=metadata.get("recipe_name"),
        launch_mode="stagehand_first",
        status="planned",
    )


@router.post("/{meeting_id}/live/start", response_model=MeetingLiveStartRead)
async def start_live_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status != "active":
        raise HTTPException(status_code=400, detail="Meeting is not active")

    workspace = db.get(Workspace, meeting.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    runtime_session = ensure_runtime_session(db, meeting)
    bind = getattr(db.get_bind(), "engine", db.get_bind())
    runtime = runtime_manager.get(runtime_session.id) or runtime_manager.create(
        runtime_session.id,
        runtime_session.workspace_id,
        db_factory=lambda: Session(bind),
        event_sink=build_runtime_event_sink(meeting.id, lambda: Session(bind)),
        meeting_id=meeting.id,
    )
    if getattr(runtime, "_meeting_id", None) is None:
        runtime._meeting_id = meeting.id

    runtime_session.live_status = "starting"
    db.add(runtime_session)
    db.commit()

    try:
        result = await runtime.start(db, runtime_session, workspace)
    except ImportError as exc:
        runtime_session.live_status = "error"
        db.add(runtime_session)
        db.commit()
        raise HTTPException(status_code=503, detail=f"Live demo dependencies are not installed: {exc}") from exc
    except Exception as exc:
        runtime_session.live_status = "error"
        db.add(runtime_session)
        db.commit()
        raise HTTPException(status_code=503, detail=f"Could not start live meeting: {exc}") from exc

    db.refresh(runtime_session)
    sync_meeting_from_runtime(db, meeting, runtime_session)

    return MeetingLiveStartRead(
        mode="live",
        livekit_url=result.buyer_contract.livekit_url,
        room_name=result.buyer_contract.room_name,
        participant_token=result.buyer_contract.token,
        participant_identity=result.buyer_contract.participant_identity,
        participant_name=result.buyer_contract.participant_name,
        event_ws_url=_event_ws_url(meeting_id),
        browser_session_id=runtime_session.browser_session_id,
        capabilities_json=json.dumps(result.capabilities),
        message="Live meeting ready",
    )


def _get_runtime_for_meeting(db: Session, meeting_id: str) -> tuple[MeetingSessionV2, DemoSession]:
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.runtime_session_id:
        raise HTTPException(status_code=404, detail="No live runtime for this meeting")
    runtime_session = db.get(DemoSession, meeting.runtime_session_id)
    if runtime_session is None:
        raise HTTPException(status_code=404, detail="Live runtime session not found")
    return meeting, runtime_session


@router.post("/{meeting_id}/controls/pause", response_model=MeetingLiveControlRead)
async def pause_live_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting, runtime_session = _get_runtime_for_meeting(db, meeting_id)
    runtime = runtime_manager.get(runtime_session.id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this meeting")
    payload = await runtime.pause()
    db.refresh(runtime_session)
    sync_meeting_from_runtime(db, meeting, runtime_session)
    return MeetingLiveControlRead(**payload)


@router.post("/{meeting_id}/controls/resume", response_model=MeetingLiveControlRead)
async def resume_live_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting, runtime_session = _get_runtime_for_meeting(db, meeting_id)
    runtime = runtime_manager.get(runtime_session.id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this meeting")
    payload = await runtime.resume()
    db.refresh(runtime_session)
    sync_meeting_from_runtime(db, meeting, runtime_session)
    return MeetingLiveControlRead(**payload)


@router.post("/{meeting_id}/controls/next-step", response_model=MeetingLiveControlRead)
async def next_live_meeting_step(meeting_id: str, db: Session = Depends(get_session)):
    meeting, runtime_session = _get_runtime_for_meeting(db, meeting_id)
    runtime = runtime_manager.get(runtime_session.id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this meeting")
    payload = await runtime.next_step()
    db.refresh(runtime_session)
    sync_meeting_from_runtime(db, meeting, runtime_session)
    return MeetingLiveControlRead(**payload)


@router.post("/{meeting_id}/controls/restart", response_model=MeetingLiveControlRead)
async def restart_live_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting, runtime_session = _get_runtime_for_meeting(db, meeting_id)
    runtime = runtime_manager.get(runtime_session.id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this meeting")
    payload = await runtime.restart()
    db.refresh(runtime_session)
    sync_meeting_from_runtime(db, meeting, runtime_session)
    return MeetingLiveControlRead(**payload)


@router.post("/{meeting_id}/live/greet")
async def greet_live_meeting(meeting_id: str, db: Session = Depends(get_session)):
    meeting, runtime_session = _get_runtime_for_meeting(db, meeting_id)
    runtime = runtime_manager.get(runtime_session.id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this meeting")

    await runtime.request_intro_greeting()
    db.refresh(runtime_session)
    sync_meeting_from_runtime(db, meeting, runtime_session)
    return {"detail": "Greeting played"}


@router.websocket("/{meeting_id}/events")
async def meeting_events(meeting_id: str, websocket: WebSocket, db: Session = Depends(get_session)):
    meeting = db.get(MeetingSessionV2, meeting_id)
    if meeting is None:
        await websocket.close(code=4404)
        return
    if not meeting.runtime_session_id:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await websocket.send_json(
        {
            "type": "connected",
            "meeting_id": meeting_id,
            "runtime_session_id": meeting.runtime_session_id,
        }
    )

    try:
        async with event_broker.subscribe(meeting.runtime_session_id) as queue:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
    except WebSocketDisconnect:
        return
