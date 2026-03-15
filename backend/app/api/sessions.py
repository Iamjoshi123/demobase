"""Demo session API routes - buyer chat, live demo control, and summaries."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.analytics.summary import generate_session_summary
from app.browser.executor import (
    close_browser_session,
    execute_action,
    execute_recipe,
    get_browser_state,
    start_browser_session,
    take_screenshot,
)
from app.config import settings
from app.database import get_session
from app.live.events import event_broker
from app.live.runtime import runtime_manager
from app.models.recipe import DemoRecipe
from app.models.session import (
    BrowserAction,
    DemoSession,
    LiveControlRead,
    LiveStartRead,
    MessageCreate,
    MessageRead,
    SessionCreate,
    SessionMessage,
    SessionRead,
    SessionSummaryRead,
)
from app.models.workspace import Workspace
from app.services.planner import plan_response
from app.voice.session import VoiceSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _event(event_type: str, **payload: object) -> dict[str, object]:
    return {
        "type": event_type,
        "timestamp": _utc_now().isoformat(),
        **payload,
    }


def _event_ws_url(session_id: str) -> str:
    backend = settings.backend_url.rstrip("/")
    if backend.startswith("https://"):
        root = "wss://" + backend[len("https://"):]
    elif backend.startswith("http://"):
        root = "ws://" + backend[len("http://"):]
    elif backend.startswith("wss://") or backend.startswith("ws://"):
        root = backend
    else:
        root = f"ws://{backend}"
    return f"{root}/api/sessions/{session_id}/events"


@router.post("", response_model=SessionRead)
def create_session(data: SessionCreate, db: Session = Depends(get_session)):
    """Create a new demo session from a workspace public token."""
    ws = db.exec(
        select(Workspace).where(
            Workspace.public_token == data.public_token,
            Workspace.is_active,
        )
    ).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Invalid demo link")

    session = DemoSession(
        workspace_id=ws.id,
        public_token=data.public_token,
        buyer_name=data.buyer_name,
        buyer_email=data.buyer_email,
        mode=data.mode,
    )
    db.add(session)

    welcome = SessionMessage(
        session_id=session.id,
        role="agent",
        content=(
            f"Welcome to the {ws.name} demo! I'm your AI assistant. "
            "You can ask me about the product, and I can show you features live. "
            "What would you like to explore?"
        ),
        message_type="text",
    )
    db.add(welcome)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionRead)
def get_session_info(session_id: str, db: Session = Depends(get_session)):
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/messages", response_model=list[MessageRead])
def get_messages(session_id: str, db: Session = Depends(get_session)):
    return db.exec(
        select(SessionMessage)
        .where(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.created_at)
    ).all()


@router.post("/{session_id}/message", response_model=MessageRead)
async def send_message(
    session_id: str,
    data: MessageCreate,
    db: Session = Depends(get_session),
):
    """Store a buyer message, plan a response, and optionally drive the live demo."""
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    user_msg = SessionMessage(
        session_id=session_id,
        role="user",
        content=data.content,
        message_type=data.message_type,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    await event_broker.publish(
        session_id,
        _event(
            "transcript",
            role="user",
            content=user_msg.content,
            message_type=user_msg.message_type,
        ),
    )

    plan = await plan_response(db, session, data.content)

    agent_msg = SessionMessage(
        session_id=session_id,
        role="agent",
        content=plan.response_text,
        message_type="text",
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

    await event_broker.publish(
        session_id,
        _event(
            "transcript",
            role="agent",
            content=agent_msg.content,
            message_type=agent_msg.message_type,
            planner_decision=agent_msg.planner_decision,
        ),
    )

    runtime = runtime_manager.get(session_id)
    if runtime is not None:
        await runtime.speak_agent_message(agent_msg.content)

    if plan.decision == "answer_and_demo" and plan.recipe_id:
        recipe = db.get(DemoRecipe, plan.recipe_id)
        if recipe and runtime is not None:
            await runtime.queue_recipe(recipe)
        elif recipe and session.browser_session_id:
            try:
                await execute_recipe(db, session_id, recipe)
            except Exception as exc:
                error_msg = SessionMessage(
                    session_id=session_id,
                    role="system",
                    content=f"Browser action failed: {exc}",
                    message_type="text",
                )
                db.add(error_msg)
                db.commit()

    return agent_msg


@router.post("/{session_id}/start-browser")
async def start_browser(session_id: str, db: Session = Depends(get_session)):
    """Start a browser session, using credentials or no-auth mode per workspace."""
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = db.get(Workspace, session.workspace_id)
    credential_ref = await start_browser_session(db, session)
    if credential_ref is None:
        raise HTTPException(
            status_code=503,
            detail="No sandbox credentials available. All accounts may be in use.",
        )

    return {
        "status": "browser_started",
        "credential_id": None if credential_ref == "no-auth" else credential_ref,
        "auth_mode": workspace.browser_auth_mode if workspace else "credentials",
    }


@router.post("/{session_id}/live/start", response_model=LiveStartRead)
async def start_live_session(session_id: str, db: Session = Depends(get_session)):
    """Create a live browser+voice session contract and start the runtime."""
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    workspace = db.get(Workspace, session.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    bind = getattr(db.get_bind(), "engine", db.get_bind())
    runtime = runtime_manager.get(session_id) or runtime_manager.create(
        session.id,
        session.workspace_id,
        db_factory=lambda: Session(bind),
    )
    session.live_status = "starting"
    db.add(session)
    db.commit()

    try:
        result = await runtime.start(db, session, workspace)
    except ImportError as exc:
        session.live_status = "error"
        db.add(session)
        db.commit()
        raise HTTPException(status_code=503, detail=f"Live demo dependencies are not installed: {exc}") from exc
    except Exception as exc:
        session.live_status = "error"
        db.add(session)
        db.commit()
        raise HTTPException(status_code=503, detail=f"Could not start live demo: {exc}") from exc

    return LiveStartRead(
        mode="live",
        livekit_url=result.buyer_contract.livekit_url,
        room_name=result.buyer_contract.room_name,
        participant_token=result.buyer_contract.token,
        participant_identity=result.buyer_contract.participant_identity,
        participant_name=result.buyer_contract.participant_name,
        event_ws_url=_event_ws_url(session_id),
        browser_session_id=session.browser_session_id,
        capabilities_json=json.dumps(result.capabilities),
        message="Live demo ready",
    )


@router.post("/{session_id}/controls/pause", response_model=LiveControlRead)
async def pause_live_session(session_id: str):
    runtime = runtime_manager.get(session_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this session")
    return LiveControlRead(**(await runtime.pause()))


@router.post("/{session_id}/controls/resume", response_model=LiveControlRead)
async def resume_live_session(session_id: str):
    runtime = runtime_manager.get(session_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this session")
    return LiveControlRead(**(await runtime.resume()))


@router.post("/{session_id}/controls/next-step", response_model=LiveControlRead)
async def advance_live_session(session_id: str):
    runtime = runtime_manager.get(session_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this session")
    return LiveControlRead(**(await runtime.next_step()))


@router.post("/{session_id}/controls/restart", response_model=LiveControlRead)
async def restart_live_session(session_id: str):
    runtime = runtime_manager.get(session_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="No live runtime for this session")
    return LiveControlRead(**(await runtime.restart()))


@router.post("/{session_id}/execute-recipe")
async def run_recipe(
    session_id: str,
    recipe_id: str,
    db: Session = Depends(get_session),
):
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    recipe = db.get(DemoRecipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    runtime = runtime_manager.get(session_id)
    if runtime is not None:
        await runtime.queue_recipe(recipe)
        return {
            "status": "queued",
            "steps_executed": 0,
            "steps_succeeded": 0,
            "results": [],
        }

    results = await execute_recipe(db, session_id, recipe)
    return {
        "status": "completed",
        "steps_executed": len(results),
        "steps_succeeded": sum(1 for r in results if r.success),
        "results": [
            {
                "action": r.action_type,
                "success": r.success,
                "narration": r.narration,
                "error": r.error,
                "screenshot": r.screenshot_b64 is not None,
            }
            for r in results
        ],
    }


@router.post("/{session_id}/explore")
async def explore_action(
    session_id: str,
    action: str,
    target: str | None = None,
    value: str | None = None,
    db: Session = Depends(get_session),
):
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await execute_action(db, session_id, action, target, value)
    return {
        "success": result.success,
        "action": result.action_type,
        "narration": result.narration,
        "error": result.error,
        "screenshot": result.screenshot_b64,
        "page_url": result.page_url,
    }


@router.get("/{session_id}/screenshot")
async def get_screenshot(session_id: str):
    screenshot = await take_screenshot(session_id)
    if not screenshot:
        raise HTTPException(status_code=404, detail="No active browser or screenshot failed")
    return {"screenshot": screenshot}


@router.get("/{session_id}/screenshot.jpg")
async def get_screenshot_image(session_id: str):
    screenshot = await take_screenshot(session_id)
    if not screenshot:
        raise HTTPException(status_code=404, detail="No active browser or screenshot failed")
    try:
        payload = base64.b64decode(screenshot)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Screenshot payload was invalid") from exc
    return Response(content=payload, media_type="image/jpeg")


@router.get("/{session_id}/browser-state")
async def get_browser_state_endpoint(session_id: str):
    state = await get_browser_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="No active browser session")
    return state


@router.post("/{session_id}/voice/start")
async def start_voice(session_id: str, db: Session = Depends(get_session)):
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    voice = VoiceSession(session_id, session.workspace_id)
    result = await voice.start()

    if result.get("mode") == "voice":
        session.mode = "voice"
        db.add(session)
        db.commit()

    return result


@router.post("/{session_id}/end")
async def end_session(session_id: str, db: Session = Depends(get_session)):
    """End a demo session, stop runtime, close browser, and generate summary."""
    session = db.get(DemoSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if runtime_manager.get(session_id) is not None:
        await runtime_manager.stop(session_id)
    else:
        await close_browser_session(db, session_id)

    session.status = "ended"
    session.live_status = "ended"
    session.ended_at = _utc_now()
    db.add(session)
    db.commit()

    summary = generate_session_summary(db, session_id)
    await event_broker.publish(
        session_id,
        _event(
            "session_ended",
            session_id=session_id,
            lead_intent_score=summary.lead_intent_score,
            summary_text=summary.summary_text,
        ),
    )

    return {
        "status": "ended",
        "summary": {
            "lead_intent_score": summary.lead_intent_score,
            "summary_text": summary.summary_text,
            "total_messages": summary.total_messages,
        },
    }


@router.get("/{session_id}/summary", response_model=SessionSummaryRead)
def get_session_summary(session_id: str, db: Session = Depends(get_session)):
    from app.models.session import SessionSummary

    summary = db.exec(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    ).first()
    if not summary:
        summary = generate_session_summary(db, session_id)
    return summary


@router.get("/{session_id}/actions")
def get_browser_actions(session_id: str, db: Session = Depends(get_session)):
    return db.exec(
        select(BrowserAction)
        .where(BrowserAction.session_id == session_id)
        .order_by(BrowserAction.created_at)
    ).all()


@router.websocket("/{session_id}/events")
async def session_events(session_id: str, websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json(_event("connected", session_id=session_id))
    try:
        async with event_broker.subscribe(session_id) as queue:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
    except WebSocketDisconnect:
        return
