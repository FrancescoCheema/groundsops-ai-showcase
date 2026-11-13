"""Allow invitations created by an operator script, with no inviting user.

Revision ID: 0025_system_invitations
Revises: 0024_organization_billing
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0025_system_invitations"
down_revision = "0024_organization_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "organization_invitations",
        "invited_by_user_id",
        existing_type=sa.String(36),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM organization_invitations WHERE invited_by_user_id IS NULL")
    op.alter_column(
        "organization_invitations",
        "invited_by_user_id",
        existing_type=sa.String(36),
        nullable=False,
    )
