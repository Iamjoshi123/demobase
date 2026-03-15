"""Sandbox credential management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.workspace import Workspace
from app.models.credential import SandboxCredential, CredentialCreate, CredentialRead
from app.services.encryption import encrypt

router = APIRouter(prefix="/workspaces/{workspace_id}/credentials", tags=["credentials"])


@router.post("", response_model=CredentialRead)
def add_credential(
    workspace_id: str,
    data: CredentialCreate,
    db: Session = Depends(get_session),
):
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    cred = SandboxCredential(
        workspace_id=workspace_id,
        label=data.label,
        login_url=data.login_url,
        username_encrypted=encrypt(data.username),
        password_encrypted=encrypt(data.password),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return CredentialRead(
        id=cred.id,
        workspace_id=cred.workspace_id,
        label=cred.label,
        login_url=cred.login_url,
        is_active=cred.is_active,
        created_at=cred.created_at,
    )


@router.get("", response_model=list[CredentialRead])
def list_credentials(workspace_id: str, db: Session = Depends(get_session)):
    creds = db.exec(
        select(SandboxCredential).where(
            SandboxCredential.workspace_id == workspace_id
        )
    ).all()
    return [
        CredentialRead(
            id=c.id,
            workspace_id=c.workspace_id,
            label=c.label,
            login_url=c.login_url,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in creds
    ]


@router.delete("/{credential_id}")
def delete_credential(
    workspace_id: str,
    credential_id: str,
    db: Session = Depends(get_session),
):
    cred = db.get(SandboxCredential, credential_id)
    if not cred or cred.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Credential not found")
    cred.is_active = False
    db.add(cred)
    db.commit()
    return {"status": "deactivated"}
