"""Sandbox credential and lock models for session isolation."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class SandboxCredential(SQLModel, table=True):
    __tablename__ = "sandbox_credentials"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    label: str = Field(default="default")  # e.g., "demo-user-1"
    login_url: str
    username_encrypted: str  # Fernet-encrypted
    password_encrypted: str  # Fernet-encrypted
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SandboxLock(SQLModel, table=True):
    __tablename__ = "sandbox_locks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    credential_id: str = Field(foreign_key="sandbox_credentials.id", index=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    released_at: Optional[datetime] = None
    is_active: bool = Field(default=True)


class CredentialCreate(SQLModel):
    label: str = "default"
    login_url: str
    username: str  # plaintext, encrypted before storage
    password: str  # plaintext, encrypted before storage


class CredentialRead(SQLModel):
    id: str
    workspace_id: str
    label: str
    login_url: str
    is_active: bool
    created_at: datetime
    # Never expose username/password
