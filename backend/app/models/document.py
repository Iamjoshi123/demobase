"""Document and DocumentChunk models for knowledge base."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    filename: str
    file_type: str  # pdf, md, txt, png, jpg, manual_note
    content_text: Optional[str] = None  # raw extracted text
    metadata_json: Optional[str] = None  # JSON string of extra metadata
    status: str = Field(default="pending")  # pending, processing, ready, error
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    chunk_index: int = Field(default=0)
    content: str
    feature_tag: Optional[str] = None  # optional tag: "dashboard", "reports", etc.
    entity_type: Optional[str] = None  # optional: "workflow", "feature", "faq"
    embedding_id: Optional[str] = None  # ID in Qdrant
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentCreate(SQLModel):
    filename: str
    file_type: str
    content_text: Optional[str] = None


class DocumentRead(SQLModel):
    id: str
    workspace_id: str
    filename: str
    file_type: str
    content_text: Optional[str]
    status: str
    created_at: datetime
