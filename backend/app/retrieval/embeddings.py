"""Embedding generation - local sentence-transformers or OpenAI fallback."""

import logging
import hashlib
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded local model
_local_model = None
_local_model_failed = False


def _get_local_model():
    """Lazy-load sentence-transformers model."""
    global _local_model, _local_model_failed
    if _local_model_failed:
        return None
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded local embedding model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"Failed to load local embedding model: {e}")
            _local_model_failed = True
            return None
    return _local_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Tries local model first, then OpenAI, then falls back to hash-based pseudo-embeddings.
    """
    if not texts:
        return []

    # Try local model
    model = _get_local_model()
    if model is not None:
        try:
            embeddings = model.encode(texts, show_progress_bar=False)
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.warning(f"Local embedding failed: {e}")

    # Try OpenAI
    if settings.has_openai:
        try:
            return _embed_openai(texts)
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}")

    # Fallback: deterministic hash-based pseudo-embeddings (384 dims to match MiniLM)
    logger.warning("Using hash-based pseudo-embeddings (no real embedding provider available)")
    return [_hash_embed(t) for t in texts]


def _embed_openai(texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings API synchronously."""
    resp = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": "text-embedding-3-small", "input": texts},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    """Generate a deterministic pseudo-embedding from text hash. For dev/testing only."""
    h = hashlib.sha512(text.encode()).hexdigest()
    # Expand hash to fill dimensions
    while len(h) < dim * 2:
        h += hashlib.sha512(h.encode()).hexdigest()
    return [int(h[i*2:i*2+2], 16) / 255.0 - 0.5 for i in range(dim)]


def embedding_dimension() -> int:
    """Return the dimensionality of the current embedding model."""
    model = _get_local_model()
    if model is not None:
        return model.get_sentence_embedding_dimension()
    if settings.has_openai:
        return 1536  # text-embedding-3-small
    return 384  # hash fallback matches MiniLM dimensions
