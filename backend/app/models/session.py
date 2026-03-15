"""Session, message, browser action, and summary models."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class DemoSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    public_token: str = Field(index=True)  # workspace public token used to join
    status: str = Field(default="active")  # active, ended, error
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    mode: str = Field(default="text")  # text, voice, live
    credential_id: Optional[str] = None  # locked credential
    browser_session_id: Optional[str] = None
    live_status: str = Field(default="idle")  # idle, starting, live, paused, error, ended
    active_recipe_id: Optional[str] = None
    current_step_index: int = Field(default=0)
    live_room_name: Optional[str] = None
    live_participant_identity: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None


class SessionMessage(SQLModel, table=True):
    __tablename__ = "session_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    role: str  # user, agent, system
    content: str
    message_type: str = Field(default="text")  # text, voice_transcript, action_narration
    planner_decision: Optional[str] = None  # answer_only, answer_and_demo, clarify, escalate, refuse
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BrowserAction(SQLModel, table=True):
    __tablename__ = "browser_actions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    action_type: str  # navigate, click, type, screenshot, wait, scroll
    target: Optional[str] = None
    value: Optional[str] = None
    status: str = Field(default="pending")  # pending, running, success, error
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    narration: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionSummary(SQLModel, table=True):
    __tablename__ = "session_summaries"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True, index=True)
    summary_text: str = ""
    top_questions: str = "[]"  # JSON array
    features_interest: str = "[]"  # JSON array
    objections: str = "[]"  # JSON array
    unresolved_items: str = "[]"  # JSON array
    escalation_reasons: str = "[]"  # JSON array
    lead_intent_score: int = Field(default=0)  # 0-100
    total_messages: int = Field(default=0)
    total_actions: int = Field(default=0)
    duration_seconds: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionCreate(SQLModel):
    public_token: str
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    mode: str = "text"


class SessionRead(SQLModel):
    id: str
    workspace_id: str
    status: str
    buyer_name: Optional[str]
    buyer_email: Optional[str]
    mode: str
    live_status: str
    active_recipe_id: Optional[str]
    current_step_index: int
    live_room_name: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]


class MessageCreate(SQLModel):
    content: str
    message_type: str = "text"


class MessageRead(SQLModel):
    id: str
    session_id: str
    role: str
    content: str
    message_type: str
    planner_decision: Optional[str]
    created_at: datetime


class SessionSummaryRead(SQLModel):
    id: str
    session_id: str
    summary_text: str
    top_questions: str
    features_interest: str
    objections: str
    unresolved_items: str
    escalation_reasons: str
    lead_intent_score: int
    total_messages: int
    total_actions: int
    duration_seconds: int
    created_at: datetime


class LiveStartRead(SQLModel):
    mode: str
    livekit_url: Optional[str] = None
    room_name: Optional[str] = None
    participant_token: Optional[str] = None
    participant_identity: Optional[str] = None
    participant_name: Optional[str] = None
    event_ws_url: Optional[str] = None
    browser_session_id: Optional[str] = None
    capabilities_json: str = "{}"
    message: Optional[str] = None


class LiveControlRead(SQLModel):
    session_id: str
    live_status: str
    active_recipe_id: Optional[str] = None
    current_step_index: int = 0
    detail: Optional[str] = None
