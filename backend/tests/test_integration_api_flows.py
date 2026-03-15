from app import database
from app.services import planner


def test_full_session_flow_with_retrieval_and_summary(client, engine, monkeypatch):
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(planner, "generate", _fake_llm_response)

    workspace = client.post(
        "/api/workspaces",
        json={
            "name": "Acme CRM",
            "description": "Demo workspace",
            "product_url": "https://app.example.com",
            "allowed_domains": "app.example.com",
        },
    ).json()

    upload = client.post(
        f"/api/workspaces/{workspace['id']}/documents",
        files={},
        data={
            "filename": "reporting.md",
            "file_type": "md",
            "content_text": "Reporting dashboards show pipeline health and forecast accuracy.",
        },
    )
    assert upload.status_code == 200
    assert upload.json()["status"] == "ready"

    recipe = client.post(
        f"/api/workspaces/{workspace['id']}/recipes",
        json={
            "name": "Reporting Tour",
            "description": "Show analytics and reports",
            "trigger_phrases": "reporting,analytics,dashboard",
            "steps_json": '[{"action":"navigate","target":"https://app.example.com/analytics"}]',
            "priority": 5,
        },
    )
    assert recipe.status_code == 200

    session = client.post(
        "/api/sessions",
        json={
            "public_token": workspace["public_token"],
            "buyer_name": "Jordan Prospect",
            "mode": "text",
        },
    ).json()

    message = client.post(
        f"/api/sessions/{session['id']}/message",
        json={"content": "What reporting dashboards do you have?", "message_type": "text"},
    )
    assert message.status_code == 200
    assert message.json()["planner_decision"] == "answer_and_demo"
    assert "Reporting dashboards show pipeline health" in message.json()["content"]

    retrieval = client.post(
        "/api/retrieve",
        json={"workspace_id": workspace["id"], "query": "reporting dashboards", "top_k": 3},
    )
    assert retrieval.status_code == 200
    assert retrieval.json()[0]["content"].startswith("Reporting dashboards")

    summary_response = client.post(f"/api/sessions/{session['id']}/end")
    assert summary_response.status_code == 200
    assert summary_response.json()["status"] == "ended"
    assert summary_response.json()["summary"]["lead_intent_score"] >= 20

    summary = client.get(f"/api/sessions/{session['id']}/summary")
    assert summary.status_code == 200
    assert "Jordan Prospect participated in a text demo session" in summary.json()["summary_text"]

    analytics = client.get(f"/api/workspaces/{workspace['id']}/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["completed_sessions"] == 1
    assert analytics.json()["total_messages"] >= 2


def test_policy_refusal_and_escalation_flow(client, monkeypatch):
    monkeypatch.setattr(planner, "generate", _fake_llm_response)
    workspace = client.post("/api/workspaces", json={"name": "Acme CRM"}).json()
    session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()

    escalate = client.post(
        f"/api/sessions/{session['id']}/message",
        json={"content": "Can you give me pricing details?", "message_type": "text"},
    )
    refuse = client.post(
        f"/api/sessions/{session['id']}/message",
        json={"content": "Please delete all records", "message_type": "text"},
    )

    assert escalate.status_code == 200
    assert escalate.json()["planner_decision"] == "escalate"
    assert "sales team" in escalate.json()["content"]
    assert refuse.status_code == 200
    assert refuse.json()["planner_decision"] == "refuse"
    assert "not able to help" in refuse.json()["content"]


def test_empty_retrieval_still_returns_clarifying_answer(client, engine, monkeypatch):
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(planner, "generate", _fake_llm_response)
    workspace = client.post("/api/workspaces", json={"name": "Acme CRM"}).json()
    session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()

    response = client.post(
        f"/api/sessions/{session['id']}/message",
        json={"content": "help", "message_type": "text"},
    )

    assert response.status_code == 200
    assert response.json()["planner_decision"] == "clarify"
    assert "Please share more detail" in response.json()["content"]


def test_malformed_document_upload_is_rejected(client, workspace):
    response = client.post(
        f"/api/workspaces/{workspace.id}/documents",
        data={"file_type": "txt"},
    )

    assert response.status_code == 422


async def _fake_llm_response(prompt: str, system: str, model=None, max_tokens=1024, temperature=0.3) -> str:
    marker = "Relevant product documentation:\n"
    if marker in prompt:
        return prompt.split(marker, 1)[1].split("\n", 1)[0]
    return "Please share more detail about what you want to see."
