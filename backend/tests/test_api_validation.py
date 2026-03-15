def test_workspace_create_requires_name(client):
    response = client.post("/api/workspaces", json={"description": "missing name"})

    assert response.status_code == 422


def test_session_create_requires_public_token(client):
    response = client.post("/api/sessions", json={"buyer_name": "No token"})

    assert response.status_code == 422


def test_recipe_create_requires_name_and_steps(client, workspace):
    response = client.post(
        f"/api/workspaces/{workspace.id}/recipes",
        json={"priority": 1},
    )

    assert response.status_code == 422


def test_policy_create_requires_pattern(client, workspace):
    response = client.post(
        f"/api/workspaces/{workspace.id}/policies",
        json={"rule_type": "blocked_topic", "action": "refuse", "severity": "high"},
    )

    assert response.status_code == 422
