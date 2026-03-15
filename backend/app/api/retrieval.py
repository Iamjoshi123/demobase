"""Internal retrieval and planning API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session
from app.database import get_session
from app.retrieval.vector_store import search as vector_search

router = APIRouter(tags=["retrieval"])


class RetrieveRequest(BaseModel):
    workspace_id: str
    query: str
    top_k: int = 5


class RetrieveResult(BaseModel):
    content: str
    document_id: Optional[str] = None
    feature_tag: Optional[str] = None
    score: float


@router.post("/retrieve", response_model=list[RetrieveResult])
def retrieve(data: RetrieveRequest, db: Session = Depends(get_session)):
    """Search knowledge base for relevant content."""
    results = vector_search(data.query, data.workspace_id, data.top_k)
    return [
        RetrieveResult(
            content=r["content"],
            document_id=r.get("document_id"),
            feature_tag=r.get("feature_tag"),
            score=r.get("score", 0),
        )
        for r in results
    ]
