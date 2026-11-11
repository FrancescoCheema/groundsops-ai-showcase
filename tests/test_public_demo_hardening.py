import pytest

from groundsops.config import get_settings


@pytest.fixture
def public_demo(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "demo")
    return get_settings().demo_organization_id


def test_public_demo_blocks_creating_workspaces(client, public_demo):
    response = client.post(
        "/api/v1/auth/development-bootstrap",
        json={"organization_name": "Spam Co", "admin_email": "spam@example.com",
              "admin_display_name": "Spam"},
    )
    assert response.status_code == 404
    signup = client.post(
        "/api/v1/auth/development-signup-token",
        json={"email": "spam@example.com", "display_name": "Spam"},
    )
    assert signup.status_code == 404


def test_public_demo_only_issues_tokens_for_the_demo_workspace(
    client, create_identity, monkeypatch
):
    other_org, _ = create_identity("Real Customer")  # created before demo mode is on
    monkeypatch.setattr(get_settings(), "app_env", "demo")

    response = client.post(
        "/api/v1/auth/development-token",
        json={"organization_id": other_org, "email": "real-customer@example.com"},
    )

    assert response.status_code == 404


def test_development_sign_in_is_unchanged_outside_public_demo(client, create_identity):
    organization_id, _ = create_identity("Local Dev")
    response = client.post(
        "/api/v1/auth/development-token",
        json={"organization_id": organization_id, "email": "local-dev@example.com"},
    )
    assert response.status_code == 200
