"""Add a per-company price list and estimate defaults.

Revision ID: 0026_price_list
Revises: 0025_system_invitations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0026_price_list"
down_revision = "0025_system_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("estimate_labour_rate", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "organizations",
        sa.Column("estimate_delivery_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "organizations",
        sa.Column("estimate_tax_rate", sa.Numeric(6, 3), nullable=False, server_default="12"),
    )
    op.create_table(
        "price_list_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("material_type", sa.String(30), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("waste_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("depth", sa.Numeric(8, 2)),
        sa.Column("supplier", sa.String(200)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "material_type"),
    )
    op.create_index(
        "ix_price_list_items_organization_id", "price_list_items", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_price_list_items_organization_id", table_name="price_list_items")
    op.drop_table("price_list_items")
    op.drop_column("organizations", "estimate_tax_rate")
    op.drop_column("organizations", "estimate_delivery_cost")
    op.drop_column("organizations", "estimate_labour_rate")
