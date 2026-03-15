"""Policy evaluation engine - checks messages and actions against workspace rules."""

import re
import logging
from dataclasses import dataclass
from typing import Optional
from sqlmodel import Session, select
from app.models.policy import PolicyRule

logger = logging.getLogger(__name__)

# Built-in escalation patterns (always active)
BUILTIN_BLOCKED_PATTERNS = [
    (r"\b(pricing|discount|deal|negotiate|bargain)\b", "escalate", "Pricing/discount discussion requires human sales rep"),
    (r"\b(contract|legal|terms|agreement|procurement|NDA)\b", "escalate", "Legal/procurement topics require human involvement"),
    (
        r"\b(delete all|drop table|rm -rf|format|destroy|wipe|reset workspace|remove all users|revoke all access)\b",
        "refuse",
        "Destructive operations not allowed",
    ),
]


@dataclass
class PolicyDecision:
    allowed: bool
    decision: str  # allow, refuse, escalate, warn
    matched_rules: list[str]
    reason: Optional[str] = None


def evaluate_policy(
    db: Session,
    workspace_id: str,
    user_message: str,
    proposed_action: Optional[str] = None,
    target_url: Optional[str] = None,
) -> PolicyDecision:
    """Evaluate a user message and/or proposed action against workspace policies.

    Returns a PolicyDecision indicating whether the action is allowed.
    """
    matched_rules = []
    worst_action = "allow"
    reason = None

    text_to_check = f"{user_message} {proposed_action or ''} {target_url or ''}".lower()

    # Check built-in patterns first
    for pattern, action, desc in BUILTIN_BLOCKED_PATTERNS:
        if re.search(pattern, text_to_check, re.IGNORECASE):
            matched_rules.append(f"builtin:{desc}")
            if _severity_rank(action) > _severity_rank(worst_action):
                worst_action = action
                reason = desc

    # Check workspace-specific policy rules
    statement = select(PolicyRule).where(
        PolicyRule.workspace_id == workspace_id,
        PolicyRule.is_active,
    )
    rules = db.exec(statement).all()

    for rule in rules:
        try:
            if re.search(rule.pattern, text_to_check, re.IGNORECASE):
                matched_rules.append(f"{rule.rule_type}:{rule.description or rule.pattern}")
                if _severity_rank(rule.action) > _severity_rank(worst_action):
                    worst_action = rule.action
                    reason = rule.description or f"Policy rule matched: {rule.pattern}"
        except re.error:
            logger.warning(f"Invalid regex in policy rule {rule.id}: {rule.pattern}")

    # Check domain restrictions if target_url provided
    if target_url:
        from app.models.workspace import Workspace
        ws = db.get(Workspace, workspace_id)
        if ws and ws.allowed_domains:
            allowed = [d.strip() for d in ws.allowed_domains.split(",") if d.strip()]
            if allowed and not any(domain in target_url for domain in allowed):
                matched_rules.append(f"domain_restriction:{target_url}")
                worst_action = "refuse"
                reason = f"URL {target_url} is outside allowed domains"

    return PolicyDecision(
        allowed=worst_action == "allow",
        decision=worst_action,
        matched_rules=matched_rules,
        reason=reason,
    )


def _severity_rank(action: str) -> int:
    """Rank action severity for comparison."""
    return {"allow": 0, "warn": 1, "escalate": 2, "refuse": 3}.get(action, 0)
