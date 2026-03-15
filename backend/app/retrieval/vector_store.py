"""Qdrant vector store integration for document retrieval."""

import logging
from app.config import settings
from app.retrieval.embeddings import embed_texts, embedding_dimension

logger = logging.getLogger(__name__)

_client = None
_qdrant_available = False


def _get_client():
    """Lazy-initialize Qdrant client."""
    global _client, _qdrant_available
    if _client is not None:
        return _client
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        _client = QdrantClient(url=settings.qdrant_url, timeout=5)
        # Ensure collection exists
        collections = [c.name for c in _client.get_collections().collections]
        if settings.qdrant_collection not in collections:
            _client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=embedding_dimension(),
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")
        _qdrant_available = True
        return _client
    except Exception as e:
        logger.warning(f"Qdrant not available: {e}. Using keyword fallback.")
        _qdrant_available = False
        return None


def store_chunks(chunks: list[dict], workspace_id: str, document_id: str) -> list[str]:
    """Store document chunks as vectors in Qdrant.

    Args:
        chunks: List of dicts with 'content', 'chunk_index', 'feature_tag'
        workspace_id: Workspace ID for filtering
        document_id: Source document ID

    Returns:
        List of point IDs stored in Qdrant
    """
    client = _get_client()
    if client is None:
        logger.warning("Qdrant unavailable, chunks stored in DB only")
        return []

    from qdrant_client.models import PointStruct
    import uuid

    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)
    if not embeddings:
        return []

    points = []
    point_ids = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        pid = str(uuid.uuid4())
        point_ids.append(pid)
        points.append(PointStruct(
            id=pid,
            vector=embedding,
            payload={
                "workspace_id": workspace_id,
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "feature_tag": chunk.get("feature_tag"),
            },
        ))

    try:
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=points,
        )
        logger.info(f"Stored {len(points)} vectors for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to store vectors: {e}")
        return []

    return point_ids


def search(query: str, workspace_id: str, top_k: int = 5) -> list[dict]:
    """Search for relevant chunks using vector similarity.

    Falls back to keyword matching if Qdrant is unavailable.
    """
    client = _get_client()
    if client is None:
        return _keyword_fallback(query, workspace_id, top_k)

    try:
        query_embedding = embed_texts([query])
        if not query_embedding:
            return _keyword_fallback(query, workspace_id, top_k)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = Filter(
            must=[FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
        )
        if hasattr(client, "search"):
            results = client.search(
                collection_name=settings.qdrant_collection,
                query_vector=query_embedding[0],
                query_filter=query_filter,
                limit=top_k,
            )
        elif hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=settings.qdrant_collection,
                query=query_embedding[0],
                query_filter=query_filter,
                limit=top_k,
            )
            results = getattr(response, "points", response)
        else:
            raise AttributeError("Qdrant client does not expose search or query_points")

        return [
            {
                "content": hit.payload.get("content", ""),
                "document_id": hit.payload.get("document_id"),
                "feature_tag": hit.payload.get("feature_tag"),
                "score": hit.score,
            }
            for hit in results
        ]
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        return _keyword_fallback(query, workspace_id, top_k)


def _keyword_fallback(query: str, workspace_id: str, top_k: int) -> list[dict]:
    """Simple keyword-based fallback when Qdrant is unavailable."""
    from sqlmodel import Session as DBSession, select
    from app.database import engine
    from app.models.document import DocumentChunk

    keywords = query.lower().split()

    with DBSession(engine) as db:
        all_chunks = db.exec(
            select(DocumentChunk).where(DocumentChunk.workspace_id == workspace_id)
        ).all()

    scored = []
    for chunk in all_chunks:
        content_lower = chunk.content.lower()
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: (-x[0], x[1].chunk_index, x[1].document_id, x[1].id))

    return [
        {
            "content": chunk.content,
            "document_id": chunk.document_id,
            "feature_tag": chunk.feature_tag,
            "score": score / max(len(keywords), 1),
        }
        for score, chunk in scored[:top_k]
    ]
