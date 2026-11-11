"""Add subscription billing state to organizations.

Revision ID: 0024_organization_billing
Revises: 0023_job_completion_payments
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0024_organization_billing"
down_revision = "0023_job_completion_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "subscription_status",
            sa.String(30),
            nullable=False,
            server_default="trialing",
        ),
    )
    op.add_column("organizations", sa.Column("trial_ends_at", sa.DateTime(timezone=True)))
    op.add_column("organizations", sa.Column("current_period_end", sa.DateTime(timezone=True)))
    op.add_column("organizations", sa.Column("stripe_customer_id", sa.String(100)))
    op.add_column("organizations", sa.Column("stripe_subscription_id", sa.String(100)))
    op.create_index(
        "ix_organizations_stripe_customer_id",
        "organizations",
        ["stripe_customer_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_stripe_customer_id", table_name="organizations")
    op.drop_column("organizations", "stripe_subscription_id")
    op.drop_column("organizations", "stripe_customer_id")
    op.drop_column("organizations", "current_period_end")
    op.drop_column("organizations", "trial_ends_at")
    op.drop_column("organizations", "subscription_status")
