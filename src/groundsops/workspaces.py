"""Create company workspaces and invite their first administrator."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from groundsops.models import (
    Organization,
    OrganizationInvitation,
    OrganizationRole,
    OrganizationUser,
)


class EmailAlreadyInWorkspace(ValueError):
    """The owner email already belongs to a workspace."""


def create_workspace_with_owner_invite(
    db: Session,
    *,
    organization_name: str,
    owner_email: str,
    expires_in_days: int = 14,
    invited_by_user_id: str | None = None,
) -> tuple[Organization, OrganizationInvitation, str]:
    """Create a workspace and an admin invitation for its owner.

    Returns the organization, the invitation and the one-time acceptance token (only its hash is
    stored). ``invited_by_user_id`` is None when an operator runs this from the server.
    """
    email = owner_email.lower().strip()
    if db.scalar(select(OrganizationUser).where(OrganizationUser.email == email)) is not None:
        raise EmailAlreadyInWorkspace(email)
    organization = Organization(name=organization_name.strip())
    db.add(organization)
    db.flush()
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=organization.id,
        invited_by_user_id=invited_by_user_id,
        email=email,
        role=OrganizationRole.ADMIN.value,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )
    db.add(invitation)
    db.commit()
    db.refresh(organization)
    db.refresh(invitation)
    return organization, invitation, token
