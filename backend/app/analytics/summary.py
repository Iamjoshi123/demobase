"""Session analytics and lead scoring service."""

import json
import logging
from sqlmodel import Session, select
from app.models.session import DemoSession, SessionMessage, BrowserAction, SessionSummary

logger = logging.getLogger(__name__)


def generate_session_summary(db: Session, session_id: str) -> SessionSummary:
    """Generate analytics summary for a completed session using deterministic heuristics."""
    session = db.get(DemoSession, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    messages = db.exec(
        select(SessionMessage)
        .where(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.created_at)
    ).all()

    actions = db.exec(
        select(BrowserAction)
        .where(BrowserAction.session_id == session_id)
        .order_by(BrowserAction.created_at)
    ).all()

    user_messages = [m for m in messages if m.role == "user"]
    agent_messages = [m for m in messages if m.role == "agent"]

    # Extract questions (messages ending with ?)
    questions = [m.content for m in user_messages if "?" in m.content]

    # Detect feature interest keywords
    feature_keywords = _extract_feature_mentions(user_messages)

    # Detect objections / confusion
    objections = _extract_objections(user_messages)

    # Detect escalations
    escalations = [
        m.content for m in messages
        if m.planner_decision in ("escalate", "refuse")
    ]

    # Detect unresolved items
    unresolved = _detect_unresolved(user_messages, agent_messages)

    # Calculate duration
    duration = 0
    if session.ended_at and session.started_at:
        duration = int((session.ended_at - session.started_at).total_seconds())

    # Calculate lead intent score (heuristic)
    score = _calculate_lead_score(
        num_messages=len(user_messages),
        num_questions=len(questions),
        num_features=len(feature_keywords),
        num_actions=len(actions),
        num_objections=len(objections),
        num_escalations=len(escalations),
        duration_seconds=duration,
    )

    # Generate summary text
    summary_text = _generate_summary_text(
        session=session,
        num_messages=len(messages),
        questions=questions,
        features=feature_keywords,
        objections=objections,
        score=score,
    )

    # Check for existing summary
    existing = db.exec(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    ).first()

    if existing:
        existing.summary_text = summary_text
        existing.top_questions = json.dumps(questions[:10])
        existing.features_interest = json.dumps(feature_keywords[:10])
        existing.objections = json.dumps(objections[:10])
        existing.unresolved_items = json.dumps(unresolved[:10])
        existing.escalation_reasons = json.dumps(escalations[:10])
        existing.lead_intent_score = score
        existing.total_messages = len(messages)
        existing.total_actions = len(actions)
        existing.duration_seconds = duration
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    summary = SessionSummary(
        session_id=session_id,
        summary_text=summary_text,
        top_questions=json.dumps(questions[:10]),
        features_interest=json.dumps(feature_keywords[:10]),
        objections=json.dumps(objections[:10]),
        unresolved_items=json.dumps(unresolved[:10]),
        escalation_reasons=json.dumps(escalations[:10]),
        lead_intent_score=score,
        total_messages=len(messages),
        total_actions=len(actions),
        duration_seconds=duration,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def _extract_feature_mentions(user_messages: list[SessionMessage]) -> list[str]:
    """Extract mentioned features from user messages."""
    feature_phrases = []
    trigger_words = ["feature", "can you", "do you have", "does it", "support", "integrate", "how do", "how would", "capability"]
    for msg in user_messages:
        lower = msg.content.lower()
        for trigger in trigger_words:
            if trigger in lower:
                feature_phrases.append(msg.content[:100])
                break
    return list(set(feature_phrases))


def _extract_objections(user_messages: list[SessionMessage]) -> list[str]:
    """Extract objections and confusion signals."""
    objections = []
    markers = ["but", "however", "concern", "worried", "expensive", "complex", "difficult",
               "don't understand", "confused", "not sure", "competitor", "alternative", "problem"]
    for msg in user_messages:
        lower = msg.content.lower()
        for marker in markers:
            if marker in lower:
                objections.append(msg.content[:100])
                break
    return list(set(objections))


def _detect_unresolved(user_messages: list, agent_messages: list) -> list[str]:
    """Detect questions that may not have been fully addressed."""
    unresolved = []
    # Simple heuristic: if the last 2 user messages are questions, they may be unresolved
    recent_questions = [m.content for m in user_messages[-3:] if "?" in m.content]
    if len(recent_questions) >= 2:
        unresolved = recent_questions
    return unresolved


def _calculate_lead_score(
    num_messages: int,
    num_questions: int,
    num_features: int,
    num_actions: int,
    num_objections: int,
    num_escalations: int,
    duration_seconds: int,
) -> int:
    """Calculate a deterministic lead intent score from 0-100."""
    score = 20  # base score for showing up

    # Engagement signals (up to +40)
    score += min(num_messages * 3, 15)
    score += min(num_questions * 4, 15)
    score += min(num_actions * 2, 10)

    # Feature interest (up to +20)
    score += min(num_features * 5, 20)

    # Duration bonus (up to +10)
    if duration_seconds > 60:
        score += min(duration_seconds // 60, 10)

    # Objection penalty (up to -10)
    score -= min(num_objections * 3, 10)

    # Escalation is actually a positive signal (they want more)
    score += min(num_escalations * 3, 10)

    return max(0, min(100, score))


def _generate_summary_text(
    session: DemoSession,
    num_messages: int,
    questions: list[str],
    features: list[str],
    objections: list[str],
    score: int,
) -> str:
    """Generate a human-readable summary paragraph."""
    parts = []
    buyer = session.buyer_name or "A buyer"
    parts.append(f"{buyer} participated in a {session.mode} demo session with {num_messages} total messages.")

    if questions:
        parts.append(f"They asked {len(questions)} questions.")
    if features:
        parts.append(f"Showed interest in {len(features)} feature areas.")
    if objections:
        parts.append(f"Raised {len(objections)} concerns or objections.")

    if score >= 70:
        parts.append("Lead shows strong buying intent.")
    elif score >= 40:
        parts.append("Lead shows moderate interest, may need follow-up.")
    else:
        parts.append("Lead showed low engagement, consider re-engagement.")

    return " ".join(parts)
