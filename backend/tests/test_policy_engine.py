from app.policies.engine import evaluate_policy


def test_policy_engine_blocks_builtin_topics(session, workspace):
    result = evaluate_policy(session, workspace.id, "Can you give me pricing and discount details?")

    assert result.allowed is False
    assert result.decision == "escalate"
    assert any("builtin:" in rule for rule in result.matched_rules)


def test_policy_engine_honors_workspace_blocked_actions(session, workspace, policy_factory):
    policy_factory(
        rule_type="blocked_action",
        pattern="export customers",
        description="Customer export is blocked",
        action="refuse",
    )

    result = evaluate_policy(
        session,
        workspace.id,
        "Please export customers",
        proposed_action="export customers",
    )

    assert result.allowed is False
    assert result.decision == "refuse"
    assert result.reason == "Customer export is blocked"


def test_policy_engine_enforces_allowed_domains(session, workspace):
    result = evaluate_policy(
        session,
        workspace.id,
        "Open the admin page",
        proposed_action="navigate",
        target_url="https://evil.example.net/admin",
    )

    assert result.allowed is False
    assert result.decision == "refuse"
    assert "outside allowed domains" in result.reason


def test_policy_engine_does_not_block_product_terms_like_invoice_by_default(session, workspace):
    result = evaluate_policy(session, workspace.id, "Show me the invoice workflow and payment status screen")

    assert result.allowed is True
    assert result.decision == "allow"


def test_policy_engine_ignores_invalid_regex_rules(session, workspace, policy_factory):
    policy_factory(pattern="(", description="broken regex", action="refuse")

    result = evaluate_policy(session, workspace.id, "Normal message")

    assert result.allowed is True
    assert result.decision == "allow"
    assert result.matched_rules == []
