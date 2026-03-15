from app.services import encryption


def test_credential_api_never_leaks_secrets(client, session, workspace):
    response = client.post(
        f"/api/workspaces/{workspace.id}/credentials",
        json={
            "label": "demo-user-1",
            "login_url": "https://app.example.com/login",
            "username": "demo@example.com",
            "password": "top-secret",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "username" not in body
    assert "password" not in body
    assert "username_encrypted" not in body
    assert "password_encrypted" not in body


def test_encrypt_and_decrypt_round_trip_uses_wrapper():
    ciphertext = encryption.encrypt("sensitive-value")

    assert ciphertext != "sensitive-value"
    assert encryption.decrypt(ciphertext) == "sensitive-value"
