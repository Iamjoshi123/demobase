import json
from datetime import datetime, timedelta, timezone

from app.analytics import summary


def test_calculate_lead_score_is_deterministic():
    score = summary._calculate_lead_score(
        num_messages=8,
        num_questions=3,
        num_features=2,
        num_actions=4,
        num_objections=1,
        num_escalations=1,
        duration_seconds=240,
    )

    assert score == 69


def test_detect_unresolved_uses_recent_questions(message_factory):
    first = type("Msg", (), {"content": "Can it integrate with Salesforce?"})
    second = type("Msg", (), {"content": "What about HubSpot?"})
    third = type("Msg", (), {"content": "And Slack?"})

    unresolved = summary._detect_unresolved([first, second, third], [])

    assert unresolved == [first.content, second.content, third.content]


def test_generate_session_summary_persists_questions_objections_and_escalations(
    session,
    demo_session,
    message_factory,
    browser_action_factory,
):
    demo_session.started_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    demo_session.ended_at = datetime.now(timezone.utc)
    session.add(demo_session)
    session.commit()

    message_factory(role="user", content="Can you show me reporting dashboards?")
    message_factory(role="user", content="How does Salesforce integration work?")
    message_factory(role="user", content="I am worried this might be complex?")
    message_factory(role="agent", content="Here is the dashboard walkthrough", planner_decision="answer_and_demo")
    message_factory(role="agent", content="Pricing needs sales help", planner_decision="escalate")
    browser_action_factory(action_type="navigate", narration="Opened reporting dashboard")

    generated = summary.generate_session_summary(session, demo_session.id)

    assert generated.lead_intent_score == 56
    assert generated.total_actions == 1
    assert "Taylor Buyer participated in a text demo session" in generated.summary_text
    assert "worried this might be complex" in generated.objections
    assert "Pricing needs sales help" in generated.escalation_reasons
    assert json.loads(generated.top_questions) == [
        "Can you show me reporting dashboards?",
        "How does Salesforce integration work?",
        "I am worried this might be complex?",
    ]
    assert json.loads(generated.unresolved_items) == [
        "Can you show me reporting dashboards?",
        "How does Salesforce integration work?",
        "I am worried this might be complex?",
    ]
