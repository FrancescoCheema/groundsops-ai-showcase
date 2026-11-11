"""add persistent image generation jobs

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("design_project_id", sa.String(36), nullable=False),
        sa.Column("capture_id", sa.String(36), nullable=False),
        sa.Column("requested_by_user_id", sa.String(36), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model_version", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("mask_storage_key", sa.String(500), nullable=False),
        sa.Column("output_storage_key", sa.String(500), nullable=True),
        sa.Column("output_media_type", sa.String(50), nullable=True),
        sa.Column("provider_prediction_id", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["capture_id"], ["site_captures.id"]),
        sa.ForeignKeyConstraint(["design_project_id"], ["design_projects.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["organization_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mask_storage_key"),
    )
    for column in (
        "organization_id",
        "design_project_id",
        "capture_id",
        "requested_by_user_id",
        "status",
    ):
        op.create_index(f"ix_generation_jobs_{column}", "generation_jobs", [column])


def downgrade() -> None:
    op.drop_table("generation_jobs")
