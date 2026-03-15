"""V2 meeting domain models and API schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlmodel import Field, SQLModel


class MeetingSessionV2(SQLModel, table=True):
    __tablename__ = "v2_meeting_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    public_token: str = Field(index=True)
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    goal: Optional[str] = None
    status: str = Field(default="active")  # active, ended
    stage: str = Field(default="intro")  # intro, discover, answer, demo, handoff
    rtc_status: str = Field(default="not_started")  # not_started, ready, joined
    browser_status: str = Field(default="not_started")  # not_started, planned, connected
    current_focus: Optional[str] = None
    runtime_session_id: Optional[str] = None
    active_recipe_id: Optional[str] = None
    current_step_index: int = Field(default=0)
    live_room_name: Optional[str] = None
    live_participant_identity: Optional[str] = None
    personalization_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MeetingMessageV2(SQLModel, table=True):
    __tablename__ = "v2_meeting_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="v2_meeting_sessions.id", index=True)
    role: str  # user, agent, system
    content: str
    message_type: str = Field(default="text")
    stage: Optional[str] = None
    next_actions_json: str = Field(default="[]")
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MeetingCreate(SQLModel):
    public_token: str
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    goal: Optional[str] = None
    language: Optional[str] = None


class MeetingPreferencesUpdate(SQLModel):
    language: Optional[str] = None


class MeetingRead(SQLModel):
    id: str
    workspace_id: str
    buyer_name: Optional[str]
    buyer_email: Optional[str]
    company_name: Optional[str]
    role_title: Optional[str]
    goal: Optional[str]
    status: str
    stage: str
    rtc_status: str
    browser_status: str
    current_focus: Optional[str]
    runtime_session_id: Optional[str]
    active_recipe_id: Optional[str]
    current_step_index: int
    live_room_name: Optional[str]
    live_participant_identity: Optional[str]
    personalization_json: str
    created_at: datetime
    updated_at: datetime


class MeetingMessageCreate(SQLModel):
    content: str
    message_type: str = "text"


class MeetingMessageRead(SQLModel):
    id: str
    session_id: str
    role: str
    content: str
    message_type: str
    stage: Optional[str]
    next_actions_json: str
    metadata_json: Optional[str]
    created_at: datetime


class MeetingTurnRead(SQLModel):
    message: MeetingMessageRead
    stage: str
    policy_decision: str
    next_actions: list[str]
    citations: list[str]
    recipe_id: Optional[str] = None
    browser_instruction: Optional[str] = None
    action_strategy: Optional[str] = None
    should_handoff: bool = False


class MeetingJoinRead(SQLModel):
    room_name: str
    livekit_url: str
    participant_identity: str
    participant_name: str
    participant_token: str
    capabilities_json: str
    event_ws_url: Optional[str] = None


class MeetingBrowserPlanRead(SQLModel):
    session_id: str
    product_url: Optional[str]
    allowed_domains: list[str]
    suggested_recipe_id: Optional[str] = None
    suggested_recipe_name: Optional[str] = None
    launch_mode: str = "browser_worker"
    status: str = "planned"


class MeetingLiveStartRead(SQLModel):
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


class MeetingLiveControlRead(SQLModel):
    session_id: str
    live_status: str
    active_recipe_id: Optional[str] = None
    current_step_index: int = 0
    detail: Optional[str] = None
