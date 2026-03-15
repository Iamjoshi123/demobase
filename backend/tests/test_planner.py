import pytest

from app.policies.engine import PolicyDecision
from app.services import planner


@pytest.mark.parametrize(
    ("user_message", "context", "has_recipe", "expected"),
    [
        ("What reports are available?", "Reporting docs", False, "answer_only"),
        ("Show me the dashboard", "", True, "answer_and_demo"),
        ("dashboard", "", False, "clarify"),
        ("Need help with exports", "Export docs", True, "answer_and_demo"),
    ],
)
async def test_decide_action_paths(user_message, context, has_recipe, expected):
    assert await planner._decide_action(user_message, context, has_recipe) == expected


def test_match_recipe_prefers_highest_scoring_active_recipe(recipe_factory, session, workspace):
    low = recipe_factory(name="Overview", trigger_phrases="overview", priority=1)
    high = recipe_factory(
        name="Dashboard Tour",
        description="dashboard metrics summary",
        trigger_phrases="dashboard,metrics",
        priority=10,
    )
    recipe_factory(name="Inactive", trigger_phrases="dashboard", is_active=False, priority=50)

    result = planner._match_recipe(session, workspace.id, "Can you show me the dashboard metrics?")

    assert result is not None
    assert result.id == high.id
    assert result.id != low.id


def test_match_recipe_returns_none_when_no_recipe_matches(recipe_factory, session, workspace):
    recipe_factory(trigger_phrases="invoices,billing")

    assert planner._match_recipe(session, workspace.id, "What integrations do you support?") is None


@pytest.mark.asyncio
async def test_plan_response_refuses_when_policy_blocks(session, demo_session, monkeypatch):
    monkeypatch.setattr(
        planner,
        "evaluate_policy",
        lambda *args, **kwargs: PolicyDecision(
            allowed=False,
            decision="refuse",
            matched_rules=["policy:block"],
            reason="Blocked action",
        ),
    )

    result = await planner.plan_response(session, demo_session, "Delete all customer records")

    assert result.decision == "refuse"
    assert "Blocked action" in result.response_text
    assert result.policy_decision.decision == "refuse"


@pytest.mark.asyncio
async def test_plan_response_escalates_when_policy_requires_human(session, demo_session, monkeypatch):
    monkeypatch.setattr(
        planner,
        "evaluate_policy",
        lambda *args, **kwargs: PolicyDecision(
            allowed=False,
            decision="escalate",
            matched_rules=["builtin:pricing"],
            reason="Pricing needs a seller",
        ),
    )

    result = await planner.plan_response(session, demo_session, "Can I get a discount?")

    assert result.decision == "escalate"
    assert "sales team" in result.response_text
    assert result.policy_decision.reason == "Pricing needs a seller"


@pytest.mark.asyncio
async def test_plan_response_uses_retrieval_recipe_and_generation(
    session,
    demo_session,
    recipe_factory,
    monkeypatch,
):
    recipe = recipe_factory(name="Dashboard Tour", trigger_phrases="dashboard")
    monkeypatch.setattr(
        planner,
        "evaluate_policy",
        lambda *args, **kwargs: PolicyDecision(allowed=True, decision="allow", matched_rules=[]),
    )
    monkeypatch.setattr(
        planner,
        "vector_search",
        lambda *args, **kwargs: [
            {"content": "Dashboards update in real time.", "document_id": "doc-1"},
            {"content": "Users can filter by owner.", "document_id": "doc-2"},
        ],
    )

    async def fake_generate_response(**kwargs):
        return f"{kwargs['decision']}::{kwargs['recipe_name']}::{bool(kwargs['context'])}"

    monkeypatch.setattr(planner, "_generate_response", fake_generate_response)

    result = await planner.plan_response(session, demo_session, "Show me the dashboard")

    assert result.decision == "answer_and_demo"
    assert result.recipe_id == recipe.id
    assert result.citations == ["doc-1", "doc-2"]
    assert result.retrieval_context == "Dashboards update in real time.\n---\nUsers can filter by owner."
    assert result.response_text == "answer_and_demo::Dashboard Tour::True"


@pytest.mark.asyncio
async def test_generate_response_falls_back_to_context_when_llm_fails(monkeypatch):
    async def raising_generate(*args, **kwargs):
        raise RuntimeError("llm offline")

    monkeypatch.setattr(planner, "generate", raising_generate)

    response = await planner._generate_response(
        user_message="What reports do you have?",
        context="Reporting includes forecast, quota attainment, and activity dashboards.",
        decision="answer_only",
    )

    assert response.startswith("Based on our documentation:")
    assert "Would you like me to show you this in the product?" in response


@pytest.mark.asyncio
async def test_plan_response_includes_stagehand_live_page_context(session, demo_session, monkeypatch):
    demo_session.browser_session_id = demo_session.id
    session.add(demo_session)
    session.commit()

    monkeypatch.setattr(
        planner,
        "evaluate_policy",
        lambda *args, **kwargs: PolicyDecision(allowed=True, decision="allow", matched_rules=[]),
    )
    monkeypatch.setattr(planner, "vector_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(planner, "_match_recipe", lambda *args, **kwargs: None)

    async def fake_get_browser_state(session_id: str):
        assert session_id == demo_session.id
        return {
            "url": "https://app.example.com/reports",
            "title": "Reports",
            "visible_text": "Reply rates and team performance are visible here.",
            "stagehand_summary": "The reports screen shows performance analytics for sales teams.",
            "stagehand_active_module": "Reports",
            "stagehand_primary_actions": ["Filter reports", "Export report"],
        }

    captured: dict[str, str] = {}

    async def fake_generate_response(**kwargs):
        captured["live_page_context"] = kwargs["live_page_context"]
        return "Using live product context."

    monkeypatch.setattr(planner, "get_browser_state", fake_get_browser_state)
    monkeypatch.setattr(planner, "_generate_response", fake_generate_response)

    result = await planner.plan_response(session, demo_session, "What can I learn from this screen?")

    assert result.decision == "answer_only"
    assert "Stagehand screen summary" in captured["live_page_context"]
    assert "Primary visible actions: Filter reports, Export report" in captured["live_page_context"]
    assert result.response_text == "Using live product context."
