import pytest

from app.runtime_v3.pipeline import DemoTurnPipeline, build_verified_narration
from app.v2.models import MeetingSessionV2


async def _fake_browser_state(_session_id: str):
    return {
        "url": "https://app.example.com/invoices",
        "title": "Invoices",
        "visible_text": "Invoices Payment links Customers",
        "stagehand_summary": "The invoices area is open.",
        "stagehand_active_module": "Invoices",
        "stagehand_primary_actions": ["Create invoice", "Share payment link"],
    }


async def _fake_candidates(_session_id: str, _instruction: str):
    return [
        {
            "description": "Open the invoices view and highlight payment link options",
            "selector": "a[href='/invoices']",
            "method": "click",
        }
    ]


def _fake_retriever(_query: str, _workspace_id: str, top_k: int = 4):
    return [
        {
            "content": "Payment links are generated from an invoice and can be shared with customers.",
            "document_id": "doc-payment-links",
        }
    ]


@pytest.mark.asyncio
async def test_pipeline_prefers_stagehand_candidates_for_show_requests(session, workspace, recipe_factory):
    recipe = recipe_factory(
        name="Invoices Walkthrough",
        trigger_phrases="invoice,invoices,payment link",
    )
    meeting = MeetingSessionV2(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        runtime_session_id="runtime-1",
    )
    session.add(meeting)
    session.commit()

    pipeline = DemoTurnPipeline(
        browser_state_reader=_fake_browser_state,
        action_observer=_fake_candidates,
        retriever=_fake_retriever,
    )

    result = await pipeline.inspect(session, meeting, "Show me how to send a payment link")

    assert result.intent.mode == "show_and_tell"
    assert result.action_plan.strategy == "stagehand_first"
    assert result.action_plan.fallback_recipe_id == recipe.id
    assert result.action_plan.stagehand_instruction.startswith("Open the invoices view")


@pytest.mark.asyncio
async def test_pipeline_uses_recipe_fallback_when_no_candidates(session, workspace, recipe_factory):
    recipe = recipe_factory(name="Dashboard Tour", trigger_phrases="dashboard")
    meeting = MeetingSessionV2(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        runtime_session_id="runtime-2",
    )
    session.add(meeting)
    session.commit()

    async def no_candidates(_session_id: str, _instruction: str):
        return []

    pipeline = DemoTurnPipeline(
        browser_state_reader=_fake_browser_state,
        action_observer=no_candidates,
        retriever=_fake_retriever,
    )

    result = await pipeline.inspect(session, meeting, "Show me the dashboard")

    assert result.action_plan.strategy == "recipe_fallback"
    assert result.action_plan.fallback_recipe_id == recipe.id


@pytest.mark.asyncio
async def test_pipeline_clarifies_when_context_is_too_thin(session, workspace):
    meeting = MeetingSessionV2(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        runtime_session_id=None,
    )
    session.add(meeting)
    session.commit()

    pipeline = DemoTurnPipeline(
        browser_state_reader=_no_browser_state,
        action_observer=_no_candidates,
        retriever=lambda _query, _workspace_id, top_k=4: [],
    )

    result = await pipeline.inspect(session, meeting, "Hm?")

    assert result.intent.mode == "clarify"
    assert result.action_plan.strategy == "clarify"


def test_verified_narration_prefers_real_page_change():
    narration = build_verified_narration(
        action_type="ai_act",
        target="Open invoices",
        before_state={"title": "Dashboard", "url": "https://app.example.com/dashboard"},
        after_state={"title": "Invoices", "url": "https://app.example.com/invoices"},
        fallback_narration="Clicked invoices",
    )

    assert narration == "Opened Invoices."


async def _no_browser_state(_session_id: str):
    return None


async def _no_candidates(_session_id: str, _instruction: str):
    return []
