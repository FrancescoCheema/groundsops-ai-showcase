"""link organization users to Cognito identities

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_users",
        sa.Column("cognito_subject", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_organization_users_cognito_subject",
        "organization_users",
        ["cognito_subject"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_users_cognito_subject",
        table_name="organization_users",
    )
    op.drop_column("organization_users", "cognito_subject")
