import json
import asyncio

from app.browser import executor
from app.live import media as live_media
from app.live.room import LiveKitParticipantContract
from app.live import runtime as live_runtime


def test_create_v2_meeting_and_load_messages(client, workspace):
    created = client.post(
        "/api/v2/meetings",
        json={
            "public_token": workspace.public_token,
            "buyer_name": "Riley",
            "company_name": "Northwind",
            "role_title": "Sales Ops Lead",
            "goal": "Understand reporting workflows",
        },
    )

    assert created.status_code == 200
    assert created.json()["buyer_name"] == "Riley"
    assert created.json()["stage"] == "intro"

    messages = client.get(f"/api/v2/meetings/{created.json()['id']}/messages")
    assert messages.status_code == 200
    assert len(messages.json()) == 1
    assert "tailor this Acme CRM walkthrough" in messages.json()[0]["content"]


def test_v2_meeting_turn_returns_personalized_demo_plan(
    client,
    workspace,
    chunk_factory,
    recipe_factory,
    monkeypatch,
):
    chunk_factory(content="The analytics dashboard includes revenue forecasting and activity reporting.")
    recipe = recipe_factory(
        name="Analytics Walkthrough",
        description="Open analytics reporting",
        trigger_phrases="analytics,reports,dashboard",
    )

    async def fake_generate(prompt: str, system: str, model=None, max_tokens=1024, temperature=0.2):
        return "Riley, I'd tailor the reporting walkthrough to the metrics your team cares about most."

    monkeypatch.setattr("app.v2.orchestrator.generate", fake_generate)

    created = client.post(
        "/api/v2/meetings",
        json={
            "public_token": workspace.public_token,
            "buyer_name": "Riley",
            "company_name": "Northwind",
            "role_title": "Sales Ops Lead",
            "goal": "Understand reporting workflows",
        },
    ).json()

    response = client.post(
        f"/api/v2/meetings/{created['id']}/messages",
        json={"content": "Show me the analytics dashboard", "message_type": "text"},
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "demo"
    assert response.json()["policy_decision"] == "allow"
    assert response.json()["recipe_id"] == recipe.id
    assert response.json()["action_strategy"] == "recipe_fallback"
    assert response.json()["browser_instruction"] is None
    assert response.json()["next_actions"][0].startswith("fallback_recipe:")
    assert "Analytics Walkthrough" in response.json()["message"]["content"]


def test_v2_meeting_join_and_browser_plan_contract(
    client,
    workspace,
    recipe_factory,
    monkeypatch,
):
    recipe_factory(
        name="Dashboard Tour",
        description="Show the main dashboard",
        trigger_phrases="dashboard",
    )

    async def fake_generate(prompt: str, system: str, model=None, max_tokens=1024, temperature=0.2):
        return "I'll personalize the dashboard walkthrough for your evaluation."

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=room_name or f"meeting-{session_id}",
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    monkeypatch.setattr("app.v2.orchestrator.generate", fake_generate)
    monkeypatch.setattr("app.v2.api.create_livekit_participant", fake_contract)

    created = client.post(
        "/api/v2/meetings",
        json={
            "public_token": workspace.public_token,
            "buyer_name": "Jordan",
            "goal": "Review the dashboard",
        },
    ).json()

    client.post(
        f"/api/v2/meetings/{created['id']}/messages",
        json={"content": "Show me the dashboard", "message_type": "text"},
    )

    join = client.post(f"/api/v2/meetings/{created['id']}/join")
    browser = client.post(f"/api/v2/meetings/{created['id']}/browser-plan")

    assert join.status_code == 200
    assert join.json()["room_name"] == f"meeting-{created['id']}"
    assert json.loads(join.json()["capabilities_json"])["browser_stream"] is True

    assert browser.status_code == 200
    assert browser.json()["product_url"] == workspace.product_url
    assert browser.json()["suggested_recipe_name"] == "Dashboard Tour"
    assert browser.json()["launch_mode"] == "stagehand_first"


def test_v2_meeting_escalates_pricing_questions(client, workspace):
    created = client.post(
        "/api/v2/meetings",
        json={"public_token": workspace.public_token, "buyer_name": "Priya"},
    ).json()

    response = client.post(
        f"/api/v2/meetings/{created['id']}/messages",
        json={"content": "Can I get annual discount pricing?", "message_type": "text"},
    )

    assert response.status_code == 200
    assert response.json()["policy_decision"] == "escalate"
    assert response.json()["should_handoff"] is True
    assert "handoff_human_sales" in response.json()["next_actions"]


def test_v2_live_start_bridges_runtime_session(client, workspace, session, monkeypatch):
    workspace.browser_auth_mode = "none"
    workspace.product_url = "https://my.saleshandy.com/demo"
    session.add(workspace)
    session.commit()

    monkeypatch.setattr(executor.settings, "app_env", "test")
    monkeypatch.setattr(live_media.settings, "app_env", "test")

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=room_name or f"meeting-{session_id}",
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    monkeypatch.setattr(live_runtime, "create_livekit_participant", fake_contract)

    created = client.post(
        "/api/v2/meetings",
        json={"public_token": workspace.public_token, "buyer_name": "Riley"},
    ).json()

    start = client.post(f"/api/v2/meetings/{created['id']}/live/start")
    paused = client.post(f"/api/v2/meetings/{created['id']}/controls/pause")
    resumed = client.post(f"/api/v2/meetings/{created['id']}/controls/resume")
    meeting = client.get(f"/api/v2/meetings/{created['id']}")

    assert start.status_code == 200
    assert start.json()["mode"] == "live"
    assert start.json()["room_name"] == f"meeting-{meeting.json()['runtime_session_id']}"
    assert start.json()["event_ws_url"].endswith(f"/api/v2/meetings/{created['id']}/events")
    assert start.json()["browser_session_id"] == meeting.json()["runtime_session_id"]
    assert meeting.json()["rtc_status"] == "joined"
    assert meeting.json()["browser_status"] == "connected"
    assert paused.status_code == 200
    assert paused.json()["live_status"] == "paused"
    assert resumed.status_code == 200
    assert resumed.json()["live_status"] == "live"


def test_v2_live_greet_endpoint_plays_intro(client, workspace, session, monkeypatch):
    workspace.browser_auth_mode = "none"
    workspace.product_url = "https://www.zoho.com/in/invoice/invoicing-software-demo/"
    session.add(workspace)
    session.commit()

    monkeypatch.setattr(executor.settings, "app_env", "test")
    monkeypatch.setattr(live_media.settings, "app_env", "test")

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=room_name or f"meeting-{session_id}",
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    spoken = []

    async def fake_speak_intro(self):
        spoken.append(self.session_id)

    monkeypatch.setattr(live_runtime, "create_livekit_participant", fake_contract)
    monkeypatch.setattr(live_runtime.LiveDemoRuntime, "speak_intro_greeting", fake_speak_intro)

    created = client.post(
        "/api/v2/meetings",
        json={"public_token": workspace.public_token, "buyer_name": "Riley"},
    ).json()

    start = client.post(f"/api/v2/meetings/{created['id']}/live/start")
    greet = client.post(f"/api/v2/meetings/{created['id']}/live/greet")

    assert start.status_code == 200
    assert greet.status_code == 200
    assert greet.json()["detail"] == "Greeting played"
    assert spoken == [start.json()["browser_session_id"]]


def test_v2_live_runtime_mirrors_voice_transcript_into_v2_messages(
    client,
    workspace,
    session,
    monkeypatch,
):
    workspace.browser_auth_mode = "none"
    workspace.product_url = "https://my.saleshandy.com/demo"
    session.add(workspace)
    session.commit()

    monkeypatch.setattr(executor.settings, "app_env", "test")
    monkeypatch.setattr(live_media.settings, "app_env", "test")

    async def fake_llm_response(prompt: str, system: str, model=None, max_tokens=1024, temperature=0.3) -> str:
        return "The dashboard surfaces reply rates and engagement trends."

    def fake_contract(session_id: str, *, role: str, name: str, room_name=None, **kwargs):
        return LiveKitParticipantContract(
            livekit_url="ws://localhost:7880",
            room_name=room_name or f"meeting-{session_id}",
            participant_identity=f"{role}-{session_id}",
            participant_name=name,
            token=f"token-{role}",
        )

    monkeypatch.setattr("app.v2.orchestrator.generate", fake_llm_response)
    monkeypatch.setattr(live_runtime, "create_livekit_participant", fake_contract)

    created = client.post(
        "/api/v2/meetings",
        json={"public_token": workspace.public_token, "buyer_name": "Riley"},
    ).json()
    start = client.post(f"/api/v2/meetings/{created['id']}/live/start").json()

    runtime = live_runtime.runtime_manager.get(start["browser_session_id"])
    assert runtime is not None

    async def exercise_voice_turn():
        await runtime.handle_buyer_transcript("How do your analytics dashboards work?")
        if runtime._turn_task is not None:
            await runtime._turn_task

    asyncio.run(exercise_voice_turn())

    messages = client.get(f"/api/v2/meetings/{created['id']}/messages")
    payload = messages.json()

    assert any(item["role"] == "user" and item["message_type"] == "voice_transcript" for item in payload)
    assert any(item["role"] == "agent" and "dashboard" in item["content"].lower() for item in payload)
