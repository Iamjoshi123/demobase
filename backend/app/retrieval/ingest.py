"""Document ingestion pipeline: parse -> chunk -> embed -> store."""

import logging
from typing import Optional
from sqlmodel import Session
from app.models.document import Document, DocumentChunk
from app.retrieval.chunker import chunk_text
from app.retrieval.vector_store import store_chunks

logger = logging.getLogger(__name__)


def ingest_document(
    db: Session,
    document: Document,
    content_override: Optional[str] = None,
) -> int:
    """Process a document: extract text, chunk, embed, store.

    Args:
        db: Database session
        document: Document model instance
        content_override: Optional text to use instead of parsing the file

    Returns:
        Number of chunks created
    """
    text = content_override or document.content_text

    if not text:
        # Try parsing with Docling if available
        text = _try_docling_parse(document)

    if not text:
        document.status = "error"
        db.add(document)
        db.commit()
        logger.error(f"No text content for document {document.id}")
        return 0

    document.content_text = text
    document.status = "processing"
    db.add(document)
    db.commit()

    # Chunk the text
    chunks = chunk_text(text, feature_tag=_guess_feature_tag(document.filename, text))

    if not chunks:
        document.status = "error"
        db.add(document)
        db.commit()
        return 0

    # Store in Qdrant
    point_ids = store_chunks(chunks, document.workspace_id, document.id)

    # Store chunks in DB
    db_chunks = []
    for i, chunk_data in enumerate(chunks):
        db_chunk = DocumentChunk(
            document_id=document.id,
            workspace_id=document.workspace_id,
            chunk_index=chunk_data["chunk_index"],
            content=chunk_data["content"],
            feature_tag=chunk_data.get("feature_tag"),
            embedding_id=point_ids[i] if i < len(point_ids) else None,
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)

    document.status = "ready"
    db.add(document)
    db.commit()

    logger.info(f"Ingested document {document.id}: {len(db_chunks)} chunks")
    return len(db_chunks)


def _try_docling_parse(document: Document) -> Optional[str]:
    """Attempt to parse document with Docling."""
    try:
        from docling.document_converter import DocumentConverter
        DocumentConverter()
        # This would need a file path; for MVP we rely on content_text
        logger.info("Docling parsing would require file path - using content_text")
        return None
    except ImportError:
        logger.debug("Docling not installed, skipping file parsing")
        return None
    except Exception as e:
        logger.warning(f"Docling parsing failed: {e}")
        return None


def _guess_feature_tag(filename: str, text: str) -> Optional[str]:
    """Heuristic: guess a feature tag from filename or content."""
    filename_lower = filename.lower()
    tag_hints = {
        "dashboard": "dashboard",
        "report": "reporting",
        "analytic": "analytics",
        "setting": "settings",
        "user": "user-management",
        "integrat": "integrations",
        "api": "api",
        "billing": "billing",
        "search": "search",
        "workflow": "workflows",
    }
    for hint, tag in tag_hints.items():
        if hint in filename_lower or hint in text[:500].lower():
            return tag
    return None
