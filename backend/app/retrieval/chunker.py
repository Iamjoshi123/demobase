"""Document chunking for knowledge base ingestion."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 64


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    feature_tag: Optional[str] = None,
) -> list[dict]:
    """Split text into overlapping chunks with metadata.

    Returns a list of dicts with keys: content, chunk_index, feature_tag.
    """
    if not text or not text.strip():
        return []

    # Split by paragraphs first for more natural boundaries
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        # If adding this paragraph exceeds chunk_size, save current and start new
        if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "chunk_index": chunk_index,
                "feature_tag": feature_tag,
            })
            chunk_index += 1
            # Keep overlap from end of previous chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + para
            else:
                current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "chunk_index": chunk_index,
            "feature_tag": feature_tag,
        })

    return chunks
