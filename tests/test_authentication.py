from datetime import UTC, datetime, timedelta

import jwt

from groundsops.config import get_settings


def test_protected_endpoint_requires_bearer_token(client):
    response = client.get("/api/v1/customers")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/v1/customers", headers={"Authorization": "Bearer not-a-valid-token"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_expired_token_is_rejected(client, create_identity):
    _, auth_headers = create_identity("Expired Token Landscaping")
    valid_token = auth_headers["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(valid_token, options={"verify_signature": False})
    claims["exp"] = datetime.now(UTC) - timedelta(minutes=1)
    expired_token = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")

    response = client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_manager_cannot_create_organization_user(client, create_identity):
    _, manager_headers = create_identity("Manager Landscaping", role="manager")

    response = client.post(
        "/api/v1/users",
        headers=manager_headers,
        json={
            "email": "new-user@example.com",
            "display_name": "New User",
            "role": "crew",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permission"}


def test_authenticated_user_can_read_current_organization(client, create_identity):
    organization_id, headers = create_identity("Welcome Landscaping")
    response = client.get("/api/v1/organization", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == organization_id
    assert response.json()["name"] == "Welcome Landscaping"


def test_admin_can_update_current_organization(client, create_identity):
    _, headers = create_identity("Original Company")
    response = client.put("/api/v1/organization", headers=headers, json={"name": "Renamed Company"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Company"


def test_crew_cannot_create_customer(client, create_identity):
    _, crew_headers = create_identity("Crew Landscaping", role="crew")

    response = client.post(
        "/api/v1/customers",
        headers=crew_headers,
        json={"name": "Unauthorized Customer"},
    )

    assert response.status_code == 403


def test_spoofed_organization_header_does_not_change_token_scope(client, create_identity):
    first_org, first_headers = create_identity("First Landscaping")
    _, second_headers = create_identity("Second Landscaping")
    created = client.post(
        "/api/v1/customers",
        headers=first_headers,
        json={"name": "First Customer"},
    )
    assert created.status_code == 201

    spoofed_headers = {
        **second_headers,
        "X-Organization-ID": first_org,
    }
    response = client.get("/api/v1/customers", headers=spoofed_headers)

    assert response.status_code == 200
    assert response.json() == []
