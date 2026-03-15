"""Analytics API routes for workspace-level insights."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.workspace import Workspace
from app.models.session import DemoSession, SessionSummary

router = APIRouter(tags=["analytics"])


@router.get("/workspaces/{workspace_id}/analytics")
def get_workspace_analytics(workspace_id: str, db: Session = Depends(get_session)):
    """Aggregate analytics across all sessions in a workspace."""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    sessions = db.exec(
        select(DemoSession).where(DemoSession.workspace_id == workspace_id)
    ).all()

    summaries = db.exec(
        select(SessionSummary).where(
            SessionSummary.session_id.in_([s.id for s in sessions])
        )
    ).all() if sessions else []

    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.status == "ended")
    avg_score = (
        sum(s.lead_intent_score for s in summaries) / len(summaries)
        if summaries else 0
    )
    total_messages = sum(s.total_messages for s in summaries)
    total_actions = sum(s.total_actions for s in summaries)

    # Aggregate top questions across sessions
    all_questions = []
    all_features = []
    all_objections = []
    for s in summaries:
        try:
            all_questions.extend(json.loads(s.top_questions))
            all_features.extend(json.loads(s.features_interest))
            all_objections.extend(json.loads(s.objections))
        except json.JSONDecodeError:
            pass

    return {
        "workspace_id": workspace_id,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "average_lead_score": round(avg_score, 1),
        "total_messages": total_messages,
        "total_browser_actions": total_actions,
        "top_questions": list(set(all_questions))[:20],
        "features_interest": list(set(all_features))[:20],
        "objections": list(set(all_objections))[:10],
        "sessions": [
            {
                "id": s.id,
                "buyer_name": s.buyer_name,
                "status": s.status,
                "mode": s.mode,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            }
            for s in sessions
        ],
    }


@router.get("/workspaces/{workspace_id}/sessions")
def list_workspace_sessions(workspace_id: str, db: Session = Depends(get_session)):
    """List all sessions for a workspace with summary info."""
    sessions = db.exec(
        select(DemoSession)
        .where(DemoSession.workspace_id == workspace_id)
        .order_by(DemoSession.started_at.desc())
    ).all()

    result = []
    for session in sessions:
        summary = db.exec(
            select(SessionSummary).where(SessionSummary.session_id == session.id)
        ).first()

        result.append({
            "id": session.id,
            "buyer_name": session.buyer_name,
            "buyer_email": session.buyer_email,
            "status": session.status,
            "mode": session.mode,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "lead_intent_score": summary.lead_intent_score if summary else None,
            "total_messages": summary.total_messages if summary else 0,
        })

    return result
