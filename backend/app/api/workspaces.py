"""Workspace CRUD API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.workspace import Workspace, WorkspaceCreate, WorkspaceRead

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead)
def create_workspace(data: WorkspaceCreate, db: Session = Depends(get_session)):
    workspace = Workspace(
        name=data.name,
        description=data.description,
        product_url=data.product_url,
        allowed_domains=data.allowed_domains or "",
        browser_auth_mode=data.browser_auth_mode or "credentials",
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(db: Session = Depends(get_session)):
    return db.exec(select(Workspace).where(Workspace.is_active)).all()


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: str, db: Session = Depends(get_session)):
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.put("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(workspace_id: str, data: WorkspaceCreate, db: Session = Depends(get_session)):
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws.name = data.name
    ws.description = data.description
    ws.product_url = data.product_url
    if data.allowed_domains is not None:
        ws.allowed_domains = data.allowed_domains
    if data.browser_auth_mode:
        ws.browser_auth_mode = data.browser_auth_mode
    ws.updated_at = datetime.now(timezone.utc)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws
