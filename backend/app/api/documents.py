"""Document upload and management API routes."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from app.database import get_session
from app.models.document import Document, DocumentRead, DocumentChunk
from app.models.workspace import Workspace
from app.retrieval.ingest import ingest_document

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentRead)
async def upload_document(
    workspace_id: str,
    filename: str = Form(...),
    file_type: str = Form(default="txt"),
    content_text: str = Form(default=None),
    file: UploadFile = File(default=None),
    db: Session = Depends(get_session),
):
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get content from uploaded file or form field
    text_content = content_text
    if file:
        raw = await file.read()
        if file_type in ("txt", "md", "csv"):
            text_content = raw.decode("utf-8", errors="replace")
        else:
            text_content = content_text  # For binary files, rely on content_text or Docling

    doc = Document(
        workspace_id=workspace_id,
        filename=filename,
        file_type=file_type,
        content_text=text_content,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Ingest: chunk + embed + store
    if text_content:
        ingest_document(db, doc, content_override=text_content)
        db.refresh(doc)

    return doc


@router.get("", response_model=list[DocumentRead])
def list_documents(workspace_id: str, db: Session = Depends(get_session)):
    return db.exec(
        select(Document).where(Document.workspace_id == workspace_id)
    ).all()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(workspace_id: str, document_id: str, db: Session = Depends(get_session)):
    doc = db.get(Document, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}")
def delete_document(workspace_id: str, document_id: str, db: Session = Depends(get_session)):
    doc = db.get(Document, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete chunks
    chunks = db.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()
    for chunk in chunks:
        db.delete(chunk)

    db.delete(doc)
    db.commit()
    return {"status": "deleted"}
