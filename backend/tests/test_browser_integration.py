import json

from app.browser import executor
from app.models.session import BrowserAction
from app.services import planner
from sqlmodel import select


def test_browser_session_acquires_lock_and_releases_it(client, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")

    workspace = client.post(
        "/api/workspaces",
        json={"name": "Acme CRM", "allowed_domains": "localhost,app.example.com"},
    ).json()
    client.post(
        f"/api/workspaces/{workspace['id']}/credentials",
        json={
            "label": "demo-user-1",
            "login_url": "http://localhost/login",
            "username": "demo@example.com",
            "password": "pass123",
        },
    )
    session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()

    start = client.post(f"/api/sessions/{session['id']}/start-browser")
    end = client.post(f"/api/sessions/{session['id']}/end")

    assert start.status_code == 200
    assert start.json()["status"] == "browser_started"
    assert end.status_code == 200


def test_missing_or_locked_credentials_fall_back_to_read_only_browser_mode(client, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")
    workspace = client.post("/api/workspaces", json={"name": "Acme CRM"}).json()
    first_session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()
    second_session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()

    missing = client.post(f"/api/sessions/{first_session['id']}/start-browser")
    assert missing.status_code == 200
    assert missing.json()["status"] == "browser_started"

    client.post(
        f"/api/workspaces/{workspace['id']}/credentials",
        json={
            "label": "demo-user-1",
            "login_url": "http://localhost/login",
            "username": "demo@example.com",
            "password": "pass123",
        },
    )
    assert client.post(f"/api/sessions/{first_session['id']}/start-browser").status_code == 200
    locked = client.post(f"/api/sessions/{second_session['id']}/start-browser")
    assert locked.status_code == 200
    assert locked.json()["status"] == "browser_started"


def test_execute_recipe_logs_failures_and_continues(client, session, workspace, demo_session, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")

    client.post(
        f"/api/workspaces/{workspace.id}/credentials",
        json={
            "label": "demo-user-1",
            "login_url": "http://localhost/login",
            "username": "demo@example.com",
            "password": "pass123",
        },
    )
    client.post(f"/api/sessions/{demo_session.id}/start-browser")

    async def fail_on_click(driver, action, target=None, value=None):
        if action == "click":
            return executor.ActionResult(success=False, action_type="click", target=target, error="Click failed")
        return await original_execute_step(driver, action, target, value)

    original_execute_step = executor._execute_step
    monkeypatch.setattr(executor, "_execute_step", fail_on_click)

    recipe = client.post(
        f"/api/workspaces/{workspace.id}/recipes",
        json={
            "name": "Broken Tour",
            "description": "Contains a failing click",
            "trigger_phrases": "broken",
            "steps_json": json.dumps([
                {"action": "navigate", "target": "https://app.example.com/dashboard", "wait_ms": 0},
                {"action": "click", "target": "#missing", "wait_ms": 0},
                {"action": "screenshot", "wait_ms": 0},
            ]),
            "priority": 2,
        },
    ).json()

    result = client.post(f"/api/sessions/{demo_session.id}/execute-recipe?recipe_id={recipe['id']}")

    actions = session.exec(
        select(BrowserAction).where(BrowserAction.session_id == demo_session.id).order_by(BrowserAction.created_at)
    ).all()

    assert result.status_code == 200
    assert result.json()["steps_executed"] == 3
    assert result.json()["steps_succeeded"] == 2
    assert any(action.status == "error" and action.action_type == "click" for action in actions)
    assert actions[-1].action_type == "screenshot"


def test_blocked_route_is_refused_and_logged(client, session, workspace, demo_session, policy_factory, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")
    policy_factory(
        rule_type="blocked_route",
        pattern="/admin",
        description="Admin pages are blocked",
        action="refuse",
    )
    client.post(
        f"/api/workspaces/{workspace.id}/credentials",
        json={
            "label": "demo-user-1",
            "login_url": "http://localhost/login",
            "username": "demo@example.com",
            "password": "pass123",
        },
    )
    client.post(f"/api/sessions/{demo_session.id}/start-browser")

    result = client.post(
        f"/api/sessions/{demo_session.id}/explore",
        params={"action": "navigate", "target": "https://app.example.com/admin"},
    )

    action = session.exec(
        select(BrowserAction).where(BrowserAction.session_id == demo_session.id).order_by(BrowserAction.created_at.desc())
    ).first()

    assert result.status_code == 200
    assert result.json()["success"] is False
    assert "outside allowed domains" not in result.json()["error"]
    assert "blocked" in result.json()["narration"].lower()
    assert action.status == "error"
    assert action.error_message == result.json()["error"]


def test_send_message_triggers_recipe_and_persists_action_logs(client, workspace, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")
    monkeypatch.setattr(planner, "generate", _fake_llm_response)

    client.post(
        f"/api/workspaces/{workspace.id}/credentials",
        json={
            "label": "demo-user-1",
            "login_url": "http://localhost/login",
            "username": "demo@example.com",
            "password": "pass123",
        },
    )
    client.post(
        f"/api/workspaces/{workspace.id}/recipes",
        json={
            "name": "Dashboard Tour",
            "description": "Show the dashboard",
            "trigger_phrases": "dashboard",
            "steps_json": '[{"action":"navigate","target":"https://app.example.com/dashboard","wait_ms":0}]',
            "priority": 5,
        },
    ).json()
    session_payload = client.post("/api/sessions", json={"public_token": workspace.public_token}).json()
    client.post(f"/api/sessions/{session_payload['id']}/start-browser")

    result = client.post(
        f"/api/sessions/{session_payload['id']}/message",
        json={"content": "Show me the dashboard", "message_type": "text"},
    )
    actions = client.get(f"/api/sessions/{session_payload['id']}/actions")

    assert result.status_code == 200
    assert result.json()["planner_decision"] == "answer_and_demo"
    assert any(action["action_type"] == "navigate" for action in actions.json())


async def _fake_llm_response(prompt: str, system: str, model=None, max_tokens=1024, temperature=0.3) -> str:
    marker = "Relevant product documentation:\n"
    if marker in prompt:
        return f"Docs say: {prompt.split(marker, 1)[1].splitlines()[0]}"
    return "Please share more detail about what you want to see."
