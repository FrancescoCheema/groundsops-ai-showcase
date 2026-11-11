"""soft delete organization users

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_organization_users_deleted_at",
        "organization_users",
        ["deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_organization_users_deleted_at", table_name="organization_users")
    op.drop_column("organization_users", "deleted_at")
