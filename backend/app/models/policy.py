"""Policy rule model for guardrails and access control."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class PolicyRule(SQLModel, table=True):
    __tablename__ = "policy_rules"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    rule_type: str  # blocked_topic, blocked_action, escalation_condition, allowed_route, blocked_route
    pattern: str  # regex or keyword pattern
    description: Optional[str] = None
    action: str = Field(default="refuse")  # refuse, escalate, warn
    severity: str = Field(default="high")  # low, medium, high
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyCreate(SQLModel):
    rule_type: str
    pattern: str
    description: Optional[str] = None
    action: str = "refuse"
    severity: str = "high"


class PolicyRead(SQLModel):
    id: str
    workspace_id: str
    rule_type: str
    pattern: str
    description: Optional[str]
    action: str
    severity: str
    is_active: bool
    created_at: datetime


class PolicyEvalRequest(SQLModel):
    workspace_id: str
    user_message: str
    proposed_action: Optional[str] = None
    target_url: Optional[str] = None


class PolicyEvalResult(SQLModel):
    allowed: bool
    decision: str  # allow, refuse, escalate, warn
    matched_rules: list[str] = []
    reason: Optional[str] = None
