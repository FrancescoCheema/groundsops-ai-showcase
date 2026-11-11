"""Subscription access rules shared by authentication and billing endpoints.

Kept free of FastAPI and Stripe imports so the rules can be unit tested and
imported from ``auth`` without creating an import cycle.
"""

from datetime import UTC, datetime, timedelta

from groundsops.config import get_settings
from groundsops.models import Organization

# Stripe statuses that keep the workspace writable. ``past_due`` stays writable
# while Stripe retries the card; the UI shows a warning banner meanwhile.
# ``comped`` is a GroundsOps-only status for beta customers and partners.
PAID_STATUSES = frozenset({"active", "past_due", "comped"})


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def trial_end(organization: Organization) -> datetime:
    if organization.trial_ends_at is not None:
        return _aware(organization.trial_ends_at)
    created = _aware(organization.created_at or datetime.now(UTC))
    return created + timedelta(days=get_settings().billing_trial_days)


def has_workspace_access(organization: Organization, now: datetime | None = None) -> bool:
    if not get_settings().billing_enabled:
        return True
    status = organization.subscription_status or "trialing"
    if status in PAID_STATUSES:
        return True
    if status == "trialing":
        return (now or datetime.now(UTC)) < trial_end(organization)
    return False


def trial_days_remaining(organization: Organization, now: datetime | None = None) -> int:
    remaining = trial_end(organization) - (now or datetime.now(UTC))
    if remaining.total_seconds() <= 0:
        return 0
    return remaining.days + (1 if remaining.seconds or remaining.microseconds else 0)
