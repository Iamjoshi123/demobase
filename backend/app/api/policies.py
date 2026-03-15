"""Policy rule CRUD and evaluation API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.workspace import Workspace
from app.models.policy import PolicyRule, PolicyCreate, PolicyRead, PolicyEvalRequest, PolicyEvalResult
from app.policies.engine import evaluate_policy

router = APIRouter(tags=["policies"])


@router.post("/workspaces/{workspace_id}/policies", response_model=PolicyRead)
def create_policy(
    workspace_id: str,
    data: PolicyCreate,
    db: Session = Depends(get_session),
):
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    rule = PolicyRule(
        workspace_id=workspace_id,
        rule_type=data.rule_type,
        pattern=data.pattern,
        description=data.description,
        action=data.action,
        severity=data.severity,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/workspaces/{workspace_id}/policies", response_model=list[PolicyRead])
def list_policies(workspace_id: str, db: Session = Depends(get_session)):
    return db.exec(
        select(PolicyRule).where(PolicyRule.workspace_id == workspace_id)
    ).all()


@router.delete("/workspaces/{workspace_id}/policies/{policy_id}")
def delete_policy(
    workspace_id: str,
    policy_id: str,
    db: Session = Depends(get_session),
):
    rule = db.get(PolicyRule, policy_id)
    if not rule or rule.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    rule.is_active = False
    db.add(rule)
    db.commit()
    return {"status": "deactivated"}


@router.post("/policy/evaluate", response_model=PolicyEvalResult)
def eval_policy(data: PolicyEvalRequest, db: Session = Depends(get_session)):
    result = evaluate_policy(
        db=db,
        workspace_id=data.workspace_id,
        user_message=data.user_message,
        proposed_action=data.proposed_action,
        target_url=data.target_url,
    )
    return PolicyEvalResult(
        allowed=result.allowed,
        decision=result.decision,
        matched_rules=result.matched_rules,
        reason=result.reason,
    )
