"""add generation material estimates

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_material_estimates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("generation_job_id", sa.String(36), nullable=False, unique=True),
        sa.Column("material_type", sa.String(30), nullable=False),
        sa.Column("measurement_unit", sa.String(10), nullable=False),
        sa.Column("measured_area", sa.Numeric(14, 4), nullable=False),
        sa.Column("measured_perimeter", sa.Numeric(14, 4), nullable=False),
        sa.Column("waste_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("depth", sa.Numeric(8, 2)),
        sa.Column("order_quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("material_unit", sa.String(20), nullable=False),
        sa.Column("edging_quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("labour_hours", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("labour_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("material_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("labour_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(6, 3), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["generation_job_id"], ["generation_jobs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_generation_material_estimates_organization_id",
        "generation_material_estimates",
        ["organization_id"],
    )
    op.create_index(
        "ix_generation_material_estimates_generation_job_id",
        "generation_material_estimates",
        ["generation_job_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generation_material_estimates_generation_job_id",
        table_name="generation_material_estimates",
    )
    op.drop_index(
        "ix_generation_material_estimates_organization_id",
        table_name="generation_material_estimates",
    )
    op.drop_table("generation_material_estimates")
