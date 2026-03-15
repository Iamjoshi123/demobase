"""Basic API tests for Agentic Demo Brain."""

from fastapi.testclient import TestClient


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "Agentic Demo Brain"


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_workspace(client: TestClient):
    response = client.post("/api/workspaces", json={
        "name": "Test CRM",
        "description": "A test workspace",
        "product_url": "http://localhost:9090",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test CRM"
    assert data["public_token"]


def test_list_workspaces(client: TestClient):
    # Create a workspace first
    client.post("/api/workspaces", json={"name": "Test WS"})
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_create_recipe(client: TestClient):
    # Create workspace
    ws = client.post("/api/workspaces", json={"name": "Test"}).json()
    ws_id = ws["id"]

    response = client.post(f"/api/workspaces/{ws_id}/recipes", json={
        "name": "Test Recipe",
        "description": "Navigate to dashboard",
        "trigger_phrases": "dashboard,home",
        "steps_json": '[{"action": "navigate", "target": "http://localhost/dashboard"}]',
        "priority": 5,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Recipe"


def test_create_policy(client: TestClient):
    ws = client.post("/api/workspaces", json={"name": "Test"}).json()
    ws_id = ws["id"]

    response = client.post(f"/api/workspaces/{ws_id}/policies", json={
        "rule_type": "blocked_topic",
        "pattern": "pricing",
        "description": "Block pricing discussions",
        "action": "escalate",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["rule_type"] == "blocked_topic"


def test_session_flow(client: TestClient):
    # Create workspace
    ws = client.post("/api/workspaces", json={"name": "Test CRM"}).json()
    token = ws["public_token"]

    # Create session
    response = client.post("/api/sessions", json={
        "public_token": token,
        "buyer_name": "Jane Buyer",
        "mode": "text",
    })
    assert response.status_code == 200
    session = response.json()
    session_id = session["id"]
    assert session["status"] == "active"

    # Get messages (should have welcome)
    response = client.get(f"/api/sessions/{session_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) >= 1
    assert messages[0]["role"] == "agent"

    # End session
    response = client.post(f"/api/sessions/{session_id}/end")
    assert response.status_code == 200
    assert response.json()["status"] == "ended"


def test_policy_evaluation(client: TestClient):
    ws = client.post("/api/workspaces", json={"name": "Test"}).json()
    ws_id = ws["id"]

    response = client.post("/api/policy/evaluate", json={
        "workspace_id": ws_id,
        "user_message": "Can you give me a discount on pricing?",
    })
    assert response.status_code == 200
    data = response.json()
    # Built-in patterns should catch pricing
    assert data["decision"] in ("escalate", "refuse")
    assert not data["allowed"]


def test_invalid_session(client: TestClient):
    response = client.post("/api/sessions", json={
        "public_token": "nonexistent-token",
    })
    assert response.status_code == 404
