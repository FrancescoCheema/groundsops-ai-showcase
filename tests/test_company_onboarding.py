import jwt

from groundsops.config import get_settings


def signup_headers(client, email: str, display_name: str = "New User") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/development-signup-token",
        json={"email": email, "display_name": display_name},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_verified_identity_can_register_company(client):
    email = "owner@example.com"
    response = client.post(
        "/api/v1/onboarding/register",
        headers=signup_headers(client, email, "Owner Name"),
        json={"organization_name": "New Grounds Company"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["organization"]["name"] == "New Grounds Company"
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "admin"

    token = client.post(
        "/api/v1/auth/development-token",
        json={"organization_id": body["organization"]["id"], "email": email},
    )
    assert token.status_code == 200


def test_identity_cannot_register_twice(client):
    headers = signup_headers(client, "duplicate@example.com")
    first = client.post(
        "/api/v1/onboarding/register",
        headers=headers,
        json={"organization_name": "First Company"},
    )
    second = client.post(
        "/api/v1/onboarding/register",
        headers=headers,
        json={"organization_name": "Second Company"},
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_admin_can_invite_and_member_can_accept(client, create_identity):
    organization_id, admin_headers = create_identity("Invitation Company")
    invitation = client.post(
        "/api/v1/invitations",
        headers=admin_headers,
        json={"email": "designer@example.com", "role": "designer"},
    )
    assert invitation.status_code == 201

    accepted = client.post(
        "/api/v1/invitations/accept",
        headers=signup_headers(client, "designer@example.com", "Design User"),
        json={"token": invitation.json()["acceptance_token"]},
    )

    assert accepted.status_code == 201
    assert accepted.json()["organization_id"] == organization_id
    assert accepted.json()["role"] == "designer"


def test_invitation_rejects_wrong_email_and_reuse(client, create_identity):
    _, admin_headers = create_identity("Protected Invitation Company")
    invitation = client.post(
        "/api/v1/invitations",
        headers=admin_headers,
        json={"email": "worker@example.com", "role": "crew"},
    )
    token = invitation.json()["acceptance_token"]

    wrong_email = client.post(
        "/api/v1/invitations/accept",
        headers=signup_headers(client, "attacker@example.com"),
        json={"token": token},
    )
    accepted = client.post(
        "/api/v1/invitations/accept",
        headers=signup_headers(client, "worker@example.com"),
        json={"token": token},
    )
    reused = client.post(
        "/api/v1/invitations/accept",
        headers=signup_headers(client, "worker@example.com"),
        json={"token": token},
    )

    assert wrong_email.status_code == 403
    assert accepted.status_code == 201
    assert reused.status_code == 404


def test_admin_can_suspend_member_but_not_self(client, create_identity):
    organization_id, admin_headers = create_identity("Lifecycle Company")
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "crew@example.com",
            "display_name": "Crew User",
            "role": "crew",
        },
    )
    suspended = client.patch(
        f"/api/v1/users/{created.json()['id']}/active",
        headers=admin_headers,
        json={"active": False},
    )
    users = client.get(
        "/api/v1/users?include_inactive=true",
        headers=admin_headers,
    )
    admin = next(user for user in users.json() if user["role"] == "admin")
    self_suspend = client.patch(
        f"/api/v1/users/{admin['id']}/active",
        headers=admin_headers,
        json={"active": False},
    )
    login = client.post(
        "/api/v1/auth/development-token",
        json={"organization_id": organization_id, "email": "crew@example.com"},
    )

    assert suspended.status_code == 200
    assert suspended.json()["active"] is False
    assert self_suspend.status_code == 409
    assert login.status_code == 404


def platform_headers(headers: dict[str, str]) -> dict[str, str]:
    token = headers["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["platform_admin"] = True
    platform_token = jwt.encode(
        claims,
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {platform_token}"}


def test_company_admin_cannot_access_platform_directory(client, create_identity):
    _, admin_headers = create_identity("Tenant Admin Company")

    response = client.get("/api/v1/platform/organizations", headers=admin_headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "Platform administrator required"}


def test_platform_admin_can_list_and_suspend_cross_company_user(
    client, create_identity
):
    _, first_admin_headers = create_identity("Platform Owner Company")
    second_organization_id, second_admin_headers = create_identity(
        "Managed Tenant Company"
    )
    created = client.post(
        "/api/v1/users",
        headers=second_admin_headers,
        json={
            "email": "managed-worker@example.com",
            "display_name": "Managed Worker",
            "role": "crew",
        },
    )
    headers = platform_headers(first_admin_headers)

    organizations = client.get("/api/v1/platform/organizations", headers=headers)
    users = client.get("/api/v1/platform/users", headers=headers)
    suspended = client.patch(
        f"/api/v1/platform/users/{created.json()['id']}/active",
        headers=headers,
        json={"active": False},
    )

    assert organizations.status_code == 200
    assert {row["name"] for row in organizations.json()} == {
        "Platform Owner Company",
        "Managed Tenant Company",
    }
    assert users.status_code == 200
    managed_user = next(
        row for row in users.json() if row["email"] == "managed-worker@example.com"
    )
    assert managed_user["organization_id"] == second_organization_id
    assert managed_user["organization_name"] == "Managed Tenant Company"
    assert suspended.status_code == 200
    assert suspended.json()["active"] is False


def test_platform_admin_can_soft_delete_cross_company_user(client, create_identity):
    _, owner_headers = create_identity("Deletion Platform Owner")
    _, company_headers = create_identity("Deletion Target Company")
    created = client.post(
        "/api/v1/users",
        headers=company_headers,
        json={
            "email": "remove-me@example.com",
            "display_name": "Remove Me",
            "role": "crew",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    headers = platform_headers(owner_headers)

    response = client.delete(
        f"/api/v1/platform/users/{user_id}",
        headers=headers,
    )
    assert response.status_code == 204

    users = client.get("/api/v1/platform/users", headers=headers)
    assert users.status_code == 200
    assert user_id not in {user["id"] for user in users.json()}
