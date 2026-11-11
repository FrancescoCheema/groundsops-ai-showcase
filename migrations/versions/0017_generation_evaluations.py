"""add persistent generation evaluations

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("generation_job_id", sa.String(length=36), nullable=False),
        sa.Column("evaluator_version", sa.String(length=50), nullable=False),
        sa.Column("dimensions_match", sa.Boolean(), nullable=False),
        sa.Column("masked_change_ratio", sa.Numeric(8, 6), nullable=False),
        sa.Column("protected_change_ratio", sa.Numeric(8, 6), nullable=False),
        sa.Column("masked_change_threshold", sa.Numeric(8, 6), nullable=False),
        sa.Column("protected_change_threshold", sa.Numeric(8, 6), nullable=False),
        sa.Column("pixel_change_threshold", sa.Numeric(8, 6), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("failure_reasons", sa.JSON(), nullable=False),
        sa.Column("evaluation_latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["generation_job_id"], ["generation_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_job_id"),
    )
    op.create_index(
        "ix_generation_evaluations_organization_id",
        "generation_evaluations",
        ["organization_id"],
    )
    op.create_index(
        "ix_generation_evaluations_generation_job_id",
        "generation_evaluations",
        ["generation_job_id"],
    )
    op.create_index(
        "ix_generation_evaluations_passed",
        "generation_evaluations",
        ["passed"],
    )


def downgrade() -> None:
    op.drop_index("ix_generation_evaluations_passed", table_name="generation_evaluations")
    op.drop_index(
        "ix_generation_evaluations_generation_job_id",
        table_name="generation_evaluations",
    )
    op.drop_index(
        "ix_generation_evaluations_organization_id",
        table_name="generation_evaluations",
    )
    op.drop_table("generation_evaluations")
