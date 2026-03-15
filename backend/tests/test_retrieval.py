from sqlmodel import Session as DBSession

from app import database
from app.retrieval import vector_store


def test_keyword_fallback_returns_ranked_chunks_in_stable_order(engine, workspace, chunk_factory, monkeypatch):
    first = chunk_factory(content="Dashboard analytics and reporting for pipeline health", chunk_index=2)
    second = chunk_factory(content="Dashboard reporting helps managers forecast pipeline", chunk_index=1)
    chunk_factory(content="Billing workflows", chunk_index=3)
    monkeypatch.setattr(database, "engine", engine)

    results = vector_store._keyword_fallback("dashboard reporting pipeline", workspace.id, 5)

    assert [result["document_id"] for result in results] == [second.document_id, first.document_id]
    assert results[0]["score"] >= results[1]["score"]


def test_search_falls_back_when_embeddings_are_unavailable(monkeypatch):
    monkeypatch.setattr(vector_store, "_get_client", lambda: object())
    monkeypatch.setattr(vector_store, "embed_texts", lambda texts: [])
    monkeypatch.setattr(
        vector_store,
        "_keyword_fallback",
        lambda query, workspace_id, top_k: [{"content": "Fallback content", "score": 1.0}],
    )

    results = vector_store.search("dashboard", "ws-1", top_k=3)

    assert results == [{"content": "Fallback content", "score": 1.0}]


def test_keyword_fallback_handles_empty_retrieval(engine, workspace, monkeypatch):
    monkeypatch.setattr(database, "engine", engine)

    with DBSession(engine):
        assert vector_store._keyword_fallback("nonexistent", workspace.id, 5) == []
