"""Stripe subscription billing.

Flow:
1. An admin calls ``POST /billing/checkout`` and is redirected to Stripe Checkout.
2. Stripe calls ``POST /billing/webhook``; the signed event updates the organization.
3. Admins manage cards, invoices and cancellation in the Stripe customer portal
   via ``POST /billing/portal``.

Stripe is called over its REST API with httpx so no extra SDK is required.
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from groundsops.auth import AdminPrincipal, CurrentPrincipal, PlatformPrincipal
from groundsops.config import get_settings
from groundsops.db import get_db
from groundsops.models import Organization, OrganizationRole
from groundsops.observability import log_event
from groundsops.subscription import has_workspace_access, trial_days_remaining, trial_end

router = APIRouter(prefix="/api/v1", tags=["billing"])
DbSession = Annotated[Session, Depends(get_db)]
logger = logging.getLogger("groundsops.billing")

# Minimum lead time Stripe accepts for subscription_data[trial_end].
STRIPE_MIN_TRIAL_LEAD = timedelta(hours=49)


class BillingRead(BaseModel):
    enabled: bool
    plan_name: str
    status: str
    has_access: bool
    trial_ends_at: datetime | None
    trial_days_remaining: int
    current_period_end: datetime | None
    has_billing_account: bool
    can_manage: bool
    checkout_available: bool


class BillingRedirect(BaseModel):
    url: str


class PlatformBillingUpdate(BaseModel):
    status: Literal["comped", "trialing"]
    trial_ends_at: datetime | None = None


class PlatformBillingRead(BaseModel):
    organization_id: str
    status: str
    trial_ends_at: datetime | None


def _organization(db: Session, organization_id: str) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def _stripe_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.billing_enabled and settings.stripe_secret_key and settings.stripe_price_id
    )


def _stripe_post(path: str, data: dict[str, str]) -> dict:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.stripe_api_base}{path}",
            data=data,
            headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
            timeout=20,
        )
    except httpx.HTTPError as exc:
        log_event(logger, logging.ERROR, "stripe_request_failed", path=path, error=str(exc))
        raise HTTPException(status_code=502, detail="Billing provider is unreachable") from exc
    if response.status_code >= 400:
        log_event(
            logger,
            logging.ERROR,
            "stripe_request_rejected",
            path=path,
            status_code=response.status_code,
        )
        raise HTTPException(status_code=502, detail="Billing provider rejected the request")
    return response.json()


@router.get("/billing", response_model=BillingRead)
def get_billing(principal: CurrentPrincipal, db: DbSession) -> BillingRead:
    settings = get_settings()
    organization = _organization(db, principal.organization_id)
    trialing = (organization.subscription_status or "trialing") == "trialing"
    return BillingRead(
        enabled=settings.billing_enabled,
        plan_name=settings.billing_plan_name,
        status=organization.subscription_status or "trialing",
        has_access=has_workspace_access(organization),
        trial_ends_at=trial_end(organization) if trialing else None,
        trial_days_remaining=trial_days_remaining(organization) if trialing else 0,
        current_period_end=organization.current_period_end,
        has_billing_account=organization.stripe_customer_id is not None,
        can_manage=principal.role == OrganizationRole.ADMIN,
        checkout_available=_stripe_configured(),
    )


@router.post("/billing/checkout", response_model=BillingRedirect)
def start_checkout(principal: AdminPrincipal, db: DbSession) -> BillingRedirect:
    if not _stripe_configured():
        raise HTTPException(status_code=503, detail="Billing is not configured")
    settings = get_settings()
    organization = _organization(db, principal.organization_id)
    if organization.subscription_status in {"active", "past_due"}:
        raise HTTPException(status_code=409, detail="This workspace already has a subscription")
    if organization.stripe_customer_id is None:
        customer = _stripe_post(
            "/v1/customers",
            {
                "name": organization.name,
                "email": principal.email,
                "metadata[organization_id]": organization.id,
            },
        )
        organization.stripe_customer_id = customer["id"]
        db.commit()
    data = {
        "mode": "subscription",
        "customer": organization.stripe_customer_id,
        "client_reference_id": organization.id,
        "line_items[0][price]": settings.stripe_price_id,
        "line_items[0][quantity]": "1",
        "allow_promotion_codes": "true",
        "billing_address_collection": "auto",
        "subscription_data[metadata][organization_id]": organization.id,
        "success_url": f"{settings.app_public_url}/?billing=success",
        "cancel_url": f"{settings.app_public_url}/?billing=cancelled",
    }
    if settings.stripe_automatic_tax:
        data["automatic_tax[enabled]"] = "true"
        data["customer_update[address]"] = "auto"
    # Carry any unused in-app trial over so subscribing early never costs trial days.
    remaining_trial = trial_end(organization)
    if (
        organization.subscription_status == "trialing"
        and remaining_trial - datetime.now(UTC) > STRIPE_MIN_TRIAL_LEAD
    ):
        data["subscription_data[trial_end]"] = str(int(remaining_trial.timestamp()))
    session = _stripe_post("/v1/checkout/sessions", data)
    return BillingRedirect(url=session["url"])


@router.post("/billing/portal", response_model=BillingRedirect)
def open_billing_portal(principal: AdminPrincipal, db: DbSession) -> BillingRedirect:
    if not _stripe_configured():
        raise HTTPException(status_code=503, detail="Billing is not configured")
    organization = _organization(db, principal.organization_id)
    if organization.stripe_customer_id is None:
        raise HTTPException(status_code=409, detail="Start a subscription first")
    session = _stripe_post(
        "/v1/billing_portal/sessions",
        {
            "customer": organization.stripe_customer_id,
            "return_url": f"{get_settings().app_public_url}/?billing=portal",
        },
    )
    return BillingRedirect(url=session["url"])


def verify_stripe_signature(payload: bytes, header: str, secret: str, now: float | None = None):
    """Validate a Stripe-Signature header (scheme v1, HMAC-SHA256)."""
    timestamp = None
    signatures: list[str] = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not timestamp.isdigit() or not signatures:
        raise HTTPException(status_code=400, detail="Invalid signature header")
    tolerance = get_settings().billing_webhook_tolerance_seconds
    if abs((now or time.time()) - int(timestamp)) > tolerance:
        raise HTTPException(status_code=400, detail="Signature timestamp outside tolerance")
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise HTTPException(status_code=400, detail="Invalid signature")


def _timestamp(value: object) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if isinstance(value, int) else None


def _find_organization(db: Session, obj: dict) -> Organization | None:
    organization_id = (obj.get("metadata") or {}).get("organization_id") or obj.get(
        "client_reference_id"
    )
    if organization_id:
        organization = db.get(Organization, organization_id)
        if organization is not None:
            return organization
    customer = obj.get("customer")
    if customer:
        return db.scalar(select(Organization).where(Organization.stripe_customer_id == customer))
    return None


def _apply_subscription(organization: Organization, subscription: dict, deleted: bool) -> None:
    organization.stripe_subscription_id = subscription.get("id")
    if subscription.get("customer"):
        organization.stripe_customer_id = subscription["customer"]
    status = "canceled" if deleted else subscription.get("status", "incomplete")
    # A Stripe-side trial (carried over from the app trial) counts as paid intent.
    organization.subscription_status = "active" if status == "trialing" else status
    period_end = subscription.get("current_period_end")
    if period_end is None:
        items = (subscription.get("items") or {}).get("data") or []
        period_end = items[0].get("current_period_end") if items else None
    organization.current_period_end = _timestamp(period_end)


@router.post("/billing/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    secret = get_settings().stripe_webhook_secret
    if not get_settings().billing_enabled or not secret:
        raise HTTPException(status_code=404, detail="Not found")
    payload = await request.body()
    verify_stripe_signature(payload, stripe_signature or "", secret)
    try:
        event = json.loads(payload)
        event_type = event["type"]
        obj = event["data"]["object"]
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Malformed event") from exc

    handled = event_type in {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
    if handled:
        organization = _find_organization(db, obj)
        if organization is None:
            log_event(logger, logging.WARNING, "stripe_event_unmatched", event_type=event_type)
        elif event_type == "checkout.session.completed":
            if obj.get("customer"):
                organization.stripe_customer_id = obj["customer"]
            if obj.get("subscription"):
                organization.stripe_subscription_id = obj["subscription"]
            if organization.subscription_status not in {"active", "past_due"}:
                organization.subscription_status = "active"
        else:
            _apply_subscription(
                organization, obj, deleted=event_type == "customer.subscription.deleted"
            )
        db.commit()
        log_event(
            logger,
            logging.INFO,
            "stripe_event_processed",
            event_type=event_type,
            organization_id=organization.id if organization else None,
        )
    return {"received": True}


@router.put(
    "/platform/organizations/{organization_id}/billing",
    response_model=PlatformBillingRead,
)
def set_platform_billing(
    organization_id: str,
    payload: PlatformBillingUpdate,
    principal: PlatformPrincipal,
    db: DbSession,
) -> PlatformBillingRead:
    """Comp a beta customer or extend a trial without going through Stripe."""
    organization = _organization(db, organization_id)
    organization.subscription_status = payload.status
    if payload.trial_ends_at is not None:
        organization.trial_ends_at = payload.trial_ends_at
    db.commit()
    return PlatformBillingRead(
        organization_id=organization.id,
        status=organization.subscription_status,
        trial_ends_at=organization.trial_ends_at,
    )
