"""Workspace model - the top-level container for a product demo setup."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    product_url: Optional[str] = None
    allowed_domains: str = Field(default="")  # comma-separated
    browser_auth_mode: str = Field(default="credentials")  # credentials, none
    public_token: str = Field(default_factory=lambda: uuid.uuid4().hex[:16], unique=True, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceCreate(SQLModel):
    name: str
    description: Optional[str] = None
    product_url: Optional[str] = None
    allowed_domains: Optional[str] = None
    browser_auth_mode: str = "credentials"


class WorkspaceRead(SQLModel):
    id: str
    name: str
    description: Optional[str]
    product_url: Optional[str]
    allowed_domains: str
    browser_auth_mode: str
    public_token: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
