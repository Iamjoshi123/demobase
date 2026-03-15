import json

from app.browser import executor
from app.live.room import LiveKitParticipantContract
from app.live import runtime as live_runtime
from app.services import planner


def test_start_browser_uses_no_auth_workspace_mode(client, session, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")

    workspace = client.post(
        "/api/workspaces",
        json={
            "name": "Saleshandy Demo",
            "product_url": "https://my.saleshandy.com/demo",
            "allowed_domains": "my.saleshandy.com",
            "browser_auth_mode": "none",
        },
    ).json()
    created_session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()

    start = client.post(f"/api/sessions/{created_session['id']}/start-browser")
    state = client.get(f"/api/sessions/{created_session['id']}/browser-state")
    actions = client.get(f"/api/sessions/{created_session['id']}/actions").json()

    assert start.status_code == 200
    assert start.json() == {
        "status": "browser_started",
        "credential_id": None,
        "auth_mode": "none",
    }
    assert state.status_code == 200
    assert state.json()["url"] == "https://my.saleshandy.com/demo"
    assert actions[-1]["action_type"] == "navigate"


def test_live_start_returns_room_contract_and_control_routes(client, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        resolved_room = room_name or f"demo-{session_id}"
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=resolved_room,
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    monkeypatch.setattr(live_runtime, "create_livekit_participant", fake_contract)

    workspace = client.post(
        "/api/workspaces",
        json={
            "name": "Saleshandy Demo",
            "product_url": "https://my.saleshandy.com/demo",
            "allowed_domains": "my.saleshandy.com",
            "browser_auth_mode": "none",
        },
    ).json()
    created_session = client.post("/api/sessions", json={"public_token": workspace["public_token"]}).json()

    start = client.post(f"/api/sessions/{created_session['id']}/live/start")
    paused = client.post(f"/api/sessions/{created_session['id']}/controls/pause")
    resumed = client.post(f"/api/sessions/{created_session['id']}/controls/resume")
    advanced = client.post(f"/api/sessions/{created_session['id']}/controls/next-step")
    restarted = client.post(f"/api/sessions/{created_session['id']}/controls/restart")
    session_info = client.get(f"/api/sessions/{created_session['id']}")

    assert start.status_code == 200
    assert start.json()["mode"] == "live"
    assert start.json()["room_name"] == f"demo-{created_session['id']}"
    assert start.json()["participant_identity"] == f"buyer-{created_session['id']}"
    assert start.json()["browser_session_id"] == created_session["id"]
    assert json.loads(start.json()["capabilities_json"])["video"] is True

    assert paused.json()["live_status"] == "paused"
    assert resumed.json()["live_status"] == "live"
    assert advanced.json()["detail"] == "Advancing one recipe step"
    assert restarted.json()["detail"] == "Restarted live demo recipe"
    assert session_info.json()["mode"] == "live"
    assert session_info.json()["live_room_name"] == f"demo-{created_session['id']}"


def test_session_event_websocket_receives_transcript_updates(client, workspace, monkeypatch):
    monkeypatch.setattr(executor.settings, "app_env", "test")
    monkeypatch.setattr(planner, "generate", _fake_llm_response)

    created_session = client.post("/api/sessions", json={"public_token": workspace.public_token}).json()

    with client.websocket_connect(f"/api/sessions/{created_session['id']}/events") as websocket:
        connected = websocket.receive_json()
        response = client.post(
            f"/api/sessions/{created_session['id']}/message",
            json={"content": "How do dashboards work?", "message_type": "text"},
        )
        first_event = websocket.receive_json()
        second_event = websocket.receive_json()

    assert connected["type"] == "connected"
    assert response.status_code == 200
    assert first_event["type"] == "transcript"
    assert first_event["role"] == "user"
    assert second_event["type"] == "transcript"
    assert second_event["role"] == "agent"


async def _fake_llm_response(prompt: str, system: str, model=None, max_tokens=1024, temperature=0.3) -> str:
    return "The live product supports dashboards and analytics."
