import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.models import Organization

WEBHOOK_SECRET = "whsec_test_secret"


@pytest.fixture
def billing(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_enabled", True)
    monkeypatch.setattr(settings, "billing_trial_days", 14)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_123")
    monkeypatch.setattr(settings, "stripe_price_id", "price_123")
    monkeypatch.setattr(settings, "stripe_webhook_secret", WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "app_public_url", "https://app.example.com")
    return settings


def set_org(organization_id: str, **values) -> None:
    with SessionLocal() as db:
        organization = db.get(Organization, organization_id)
        for key, value in values.items():
            setattr(organization, key, value)
        db.commit()


def get_org(organization_id: str) -> Organization:
    with SessionLocal() as db:
        organization = db.get(Organization, organization_id)
        db.expunge(organization)
        return organization


def signed(payload: dict, secret: str = WEBHOOK_SECRET, timestamp: int | None = None):
    body = json.dumps(payload).encode()
    timestamp = timestamp or int(time.time())
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return body, {"Stripe-Signature": f"t={timestamp},v1={digest.hexdigest()}"}


def platform_headers(headers: dict[str, str]) -> dict[str, str]:
    token = headers["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["platform_admin"] = True
    elevated = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {elevated}"}


def create_customer(client, headers):
    return client.post("/api/v1/customers", headers=headers, json={"name": "Jane Doe"})


def test_billing_disabled_never_blocks_writes(client, create_identity):
    organization_id, headers = create_identity("Free Grounds")
    set_org(organization_id, trial_ends_at=datetime.now(UTC) - timedelta(days=30))

    assert create_customer(client, headers).status_code == 201
    body = client.get("/api/v1/billing", headers=headers).json()
    assert body["enabled"] is False
    assert body["has_access"] is True


def test_new_workspace_starts_with_trial(client, create_identity, billing):
    _, headers = create_identity("Trial Grounds")

    body = client.get("/api/v1/billing", headers=headers).json()

    assert body["status"] == "trialing"
    assert body["has_access"] is True
    assert body["trial_days_remaining"] == 14
    assert body["can_manage"] is True
    assert body["checkout_available"] is True


def test_expired_trial_blocks_writes_but_keeps_reads_and_billing(
    client, create_identity, billing
):
    organization_id, headers = create_identity("Expired Grounds")
    set_org(organization_id, trial_ends_at=datetime.now(UTC) - timedelta(minutes=1))

    blocked = create_customer(client, headers)
    assert blocked.status_code == 402
    assert "subscription" in blocked.json()["detail"].lower()
    assert client.get("/api/v1/customers", headers=headers).status_code == 200
    billing_state = client.get("/api/v1/billing", headers=headers).json()
    assert billing_state["has_access"] is False
    assert billing_state["trial_days_remaining"] == 0


@pytest.mark.parametrize("status", ["active", "past_due", "comped"])
def test_paid_statuses_keep_workspace_writable(client, create_identity, billing, status):
    organization_id, headers = create_identity(f"Paid {status}")
    set_org(
        organization_id,
        subscription_status=status,
        trial_ends_at=datetime.now(UTC) - timedelta(days=1),
    )

    assert create_customer(client, headers).status_code == 201


def test_canceled_subscription_blocks_writes(client, create_identity, billing):
    organization_id, headers = create_identity("Canceled Grounds")
    set_org(organization_id, subscription_status="canceled")

    assert create_customer(client, headers).status_code == 402


def test_only_admins_can_start_checkout(client, create_identity, billing):
    _, headers = create_identity("Crew Grounds", role="crew")

    assert client.post("/api/v1/billing/checkout", headers=headers).status_code == 403


def test_checkout_creates_customer_and_carries_trial(
    client, create_identity, billing, monkeypatch
):
    organization_id, headers = create_identity("Checkout Grounds")
    calls: list[tuple[str, dict]] = []

    def fake_post(url, data, headers, timeout):
        calls.append((url, data))
        assert headers["Authorization"] == "Bearer sk_test_123"
        if url.endswith("/v1/customers"):
            return httpx.Response(200, json={"id": "cus_123"})
        return httpx.Response(200, json={"url": "https://checkout.stripe.com/c/pay/cs_123"})

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post("/api/v1/billing/checkout", headers=headers)

    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.com/")
    assert calls[0][1]["metadata[organization_id]"] == organization_id
    session = calls[1][1]
    assert session["customer"] == "cus_123"
    assert session["client_reference_id"] == organization_id
    assert session["line_items[0][price]"] == "price_123"
    assert session["success_url"] == "https://app.example.com/?billing=success"
    assert "subscription_data[trial_end]" in session
    assert "automatic_tax[enabled]" not in session
    assert get_org(organization_id).stripe_customer_id == "cus_123"


def test_checkout_reports_provider_failure(client, create_identity, billing, monkeypatch):
    create_identity("Unused")
    _, headers = create_identity("Broken Stripe")
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: httpx.Response(400, json={"error": {}})
    )

    assert client.post("/api/v1/billing/checkout", headers=headers).status_code == 502


def test_checkout_unavailable_without_stripe_keys(
    client, create_identity, billing, monkeypatch
):
    monkeypatch.setattr(billing, "stripe_secret_key", None)
    _, headers = create_identity("No Keys")

    assert client.post("/api/v1/billing/checkout", headers=headers).status_code == 503


def test_portal_requires_billing_account(client, create_identity, billing):
    _, headers = create_identity("No Account")

    assert client.post("/api/v1/billing/portal", headers=headers).status_code == 409


def test_webhook_rejects_bad_signatures(client, billing):
    body, headers = signed({"type": "ping", "data": {"object": {}}}, secret="whsec_wrong")
    assert client.post("/api/v1/billing/webhook", content=body, headers=headers).status_code == 400

    stale = int(time.time()) - 3600
    body, headers = signed({"type": "ping", "data": {"object": {}}}, timestamp=stale)
    assert client.post("/api/v1/billing/webhook", content=body, headers=headers).status_code == 400

    assert client.post("/api/v1/billing/webhook", content=b"{}").status_code == 400


def test_webhook_lifecycle_updates_subscription(client, create_identity, billing):
    organization_id, headers = create_identity("Webhook Grounds")
    set_org(organization_id, trial_ends_at=datetime.now(UTC) - timedelta(days=1))
    assert create_customer(client, headers).status_code == 402

    body, sig = signed(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": organization_id,
                    "customer": "cus_live",
                    "subscription": "sub_live",
                }
            },
        }
    )
    assert client.post("/api/v1/billing/webhook", content=body, headers=sig).status_code == 200
    assert get_org(organization_id).subscription_status == "active"
    assert create_customer(client, headers).status_code == 201

    period_end = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    body, sig = signed(
        {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_live",
                    "customer": "cus_live",
                    "status": "past_due",
                    "items": {"data": [{"current_period_end": period_end}]},
                }
            },
        }
    )
    assert client.post("/api/v1/billing/webhook", content=body, headers=sig).status_code == 200
    organization = get_org(organization_id)
    assert organization.subscription_status == "past_due"
    assert int(organization.current_period_end.replace(tzinfo=UTC).timestamp()) == period_end

    body, sig = signed(
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_live", "customer": "cus_live", "status": "canceled"}},
        }
    )
    assert client.post("/api/v1/billing/webhook", content=body, headers=sig).status_code == 200
    assert get_org(organization_id).subscription_status == "canceled"
    assert create_customer(client, headers).status_code == 402


def test_webhook_ignores_unmatched_and_unknown_events(client, billing):
    for event in (
        {"type": "invoice.paid", "data": {"object": {"customer": "cus_x"}}},
        {
            "type": "customer.subscription.updated",
            "data": {"object": {"customer": "cus_unknown", "status": "active"}},
        },
    ):
        body, sig = signed(event)
        assert client.post("/api/v1/billing/webhook", content=body, headers=sig).status_code == 200


def test_webhook_disabled_when_billing_off(client):
    body, headers = signed({"type": "ping", "data": {"object": {}}})
    assert client.post("/api/v1/billing/webhook", content=body, headers=headers).status_code == 404


def test_platform_admin_can_comp_expired_workspace(client, create_identity, billing):
    organization_id, headers = create_identity("Beta Grounds")
    set_org(organization_id, trial_ends_at=datetime.now(UTC) - timedelta(days=1))
    assert create_customer(client, headers).status_code == 402

    tenant_attempt = client.put(
        f"/api/v1/platform/organizations/{organization_id}/billing",
        headers=headers,
        json={"status": "comped"},
    )
    # Refused either by the billing gate (402) or the platform-admin check (403).
    assert tenant_attempt.status_code in {402, 403}

    comped = client.put(
        f"/api/v1/platform/organizations/{organization_id}/billing",
        headers=platform_headers(headers),
        json={"status": "comped"},
    )
    assert comped.status_code == 200
    assert comped.json()["status"] == "comped"
    assert create_customer(client, headers).status_code == 201
    listing = client.get("/api/v1/platform/organizations", headers=platform_headers(headers))
    assert listing.json()[0]["subscription_status"] == "comped"
