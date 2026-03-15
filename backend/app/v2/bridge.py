"""Bridge helpers that attach the clean v2 meeting model to the existing live runtime."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable

from sqlmodel import Session

from app.models.session import DemoSession
from app.v2.models import MeetingMessageV2, MeetingSessionV2


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_runtime_session(db: Session, meeting: MeetingSessionV2) -> DemoSession:
    runtime_session = db.get(DemoSession, meeting.runtime_session_id) if meeting.runtime_session_id else None
    if runtime_session is not None:
        return runtime_session

    runtime_session = DemoSession(
        workspace_id=meeting.workspace_id,
        public_token=meeting.public_token,
        buyer_name=meeting.buyer_name,
        buyer_email=meeting.buyer_email,
        mode="live",
    )
    db.add(runtime_session)
    db.commit()
    db.refresh(runtime_session)

    meeting.runtime_session_id = runtime_session.id
    meeting.updated_at = _utc_now()
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return runtime_session


def sync_meeting_from_runtime(
    db: Session,
    meeting: MeetingSessionV2,
    runtime_session: DemoSession,
) -> MeetingSessionV2:
    meeting.runtime_session_id = runtime_session.id
    meeting.live_room_name = runtime_session.live_room_name
    meeting.live_participant_identity = runtime_session.live_participant_identity
    meeting.active_recipe_id = runtime_session.active_recipe_id
    meeting.current_step_index = runtime_session.current_step_index

    if runtime_session.status == "ended":
        meeting.status = "ended"

    if runtime_session.live_room_name:
        meeting.rtc_status = "joined" if runtime_session.live_status in {"live", "paused", "ended"} else "ready"

    if runtime_session.browser_session_id:
        meeting.browser_status = "connected" if runtime_session.live_status in {"live", "paused", "ended"} else "planned"

    if runtime_session.active_recipe_id:
        meeting.stage = "demo"

    meeting.updated_at = _utc_now()
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


def build_runtime_event_sink(
    meeting_id: str,
    session_factory: Callable[[], Session],
):
    async def sink(event: dict[str, object]) -> None:
        with session_factory() as db:
            meeting = db.get(MeetingSessionV2, meeting_id)
            if meeting is None:
                return

            if event.get("type") == "transcript":
                message = MeetingMessageV2(
                    session_id=meeting.id,
                    role=str(event.get("role") or "system"),
                    content=str(event.get("content") or ""),
                    message_type=str(event.get("message_type") or "voice_transcript"),
                    stage=meeting.stage,
                    next_actions_json=json.dumps(event.get("next_actions") or []),
                    metadata_json=json.dumps(
                        {
                            "planner_decision": event.get("planner_decision"),
                            "source": "live_runtime",
                            **(event.get("metadata") or {}),
                        }
                    ),
                )
                db.add(message)

            if event.get("type") == "runtime_error":
                message = MeetingMessageV2(
                    session_id=meeting.id,
                    role="system",
                    content=str(event.get("detail") or "Live runtime error"),
                    message_type="system",
                    stage=meeting.stage,
                    next_actions_json="[]",
                    metadata_json=json.dumps({"source": "live_runtime"}),
                )
                db.add(message)

            if event.get("type") == "recipe_started":
                meeting.stage = "demo"
                meeting.current_focus = str(event.get("recipe_name") or meeting.current_focus or "")
                meeting.active_recipe_id = str(event.get("recipe_id") or "") or meeting.active_recipe_id
                meeting.browser_status = "connected"

            if event.get("type") == "browser_action_planned":
                meeting.stage = "demo"
                meeting.current_focus = str(event.get("focus") or event.get("instruction") or meeting.current_focus or "")
                meeting.browser_status = "connected"
                db.add(
                    MeetingMessageV2(
                        session_id=meeting.id,
                        role="system",
                        content=str(event.get("instruction") or "Agent is exploring the product"),
                        message_type="action_narration",
                        stage="demo",
                        next_actions_json=json.dumps(["stagehand_browser_action"]),
                        metadata_json=json.dumps({"source": "live_runtime", "action_strategy": event.get("action_strategy")}),
                    )
                )

            if event.get("type") == "browser_action_result":
                meeting.stage = "demo"
                meeting.current_focus = str(
                    event.get("focus") or event.get("page_title") or event.get("instruction") or meeting.current_focus or ""
                )
                meeting.browser_status = "connected"
                narration = str(event.get("narration") or event.get("error") or "").strip()
                if narration:
                    db.add(
                        MeetingMessageV2(
                            session_id=meeting.id,
                            role="system",
                            content=narration,
                            message_type="action_narration",
                            stage="demo",
                            next_actions_json=json.dumps(["share_browser_context"]),
                            metadata_json=json.dumps(
                                {
                                    "source": "live_runtime",
                                    "action_strategy": event.get("action_strategy"),
                                    "page_url": event.get("page_url"),
                                    "page_title": event.get("page_title"),
                                    "success": event.get("success"),
                                }
                            ),
                        )
                    )

            if event.get("type") in {"browser_action_verified", "browser_action_failed"}:
                meeting.stage = "demo"
                meeting.current_focus = str(
                    event.get("focus") or event.get("page_title") or event.get("instruction") or meeting.current_focus or ""
                )
                meeting.browser_status = "connected"
                narration = str(event.get("narration") or event.get("error") or "").strip()
                if narration:
                    db.add(
                        MeetingMessageV2(
                            session_id=meeting.id,
                            role="system",
                            content=narration,
                            message_type="action_narration",
                            stage="demo",
                            next_actions_json=json.dumps(["verified_browser_action"] if event.get("type") == "browser_action_verified" else ["browser_action_failed"]),
                            metadata_json=json.dumps(
                                {
                                    "source": "live_runtime",
                                    "action_strategy": event.get("action_strategy"),
                                    "page_url": event.get("page_url"),
                                    "page_title": event.get("page_title"),
                                    "success": event.get("success"),
                                    "telemetry": event.get("telemetry"),
                                }
                            ),
                        )
                    )

            if event.get("type") == "browser_stage_state":
                state = str(event.get("state") or "")
                meeting.browser_status = "connected" if state in {"attaching", "live"} else "error"

            if event.get("type") == "startup_state":
                state = str(event.get("state") or "")
                if state in {"room_connected", "agent_audio_ready", "buyer_audio_ready"}:
                    meeting.rtc_status = "joined"
                if state == "browser_publisher_ready":
                    meeting.browser_status = "connected"
                if state == "failed":
                    meeting.browser_status = "error"

            if event.get("type") == "browser_action_fallback":
                meeting.stage = "demo"
                meeting.current_focus = str(
                    event.get("fallback_recipe_name") or event.get("instruction") or meeting.current_focus or ""
                )
                meeting.browser_status = "connected"

            if event.get("type") == "recipe_step":
                meeting.stage = "demo"
                meeting.browser_status = "connected"
                step_index = event.get("step_index")
                if isinstance(step_index, int):
                    meeting.current_step_index = step_index
                if event.get("recipe_id"):
                    meeting.active_recipe_id = str(event["recipe_id"])

            if event.get("type") == "status":
                live_status = str(event.get("live_status") or "")
                if live_status:
                    meeting.rtc_status = "joined" if live_status in {"live", "paused", "ended"} else "ready"
                    if meeting.browser_status == "not_started":
                        meeting.browser_status = "connected"
                step_index = event.get("current_step_index")
                if isinstance(step_index, int):
                    meeting.current_step_index = step_index

            if event.get("type") == "session_ended":
                meeting.status = "ended"
                meeting.rtc_status = "joined"
                meeting.browser_status = "connected"

            meeting.updated_at = _utc_now()
            db.add(meeting)
            db.commit()

    return sink
