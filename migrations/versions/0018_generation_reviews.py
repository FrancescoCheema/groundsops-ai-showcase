"""add generation review audit trail

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("generation_job_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["generation_job_id"], ["generation_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["organization_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_reviews_organization_id",
        "generation_reviews",
        ["organization_id"],
    )
    op.create_index(
        "ix_generation_reviews_generation_job_id",
        "generation_reviews",
        ["generation_job_id"],
    )
    op.create_index(
        "ix_generation_reviews_reviewer_user_id",
        "generation_reviews",
        ["reviewer_user_id"],
    )
    op.create_index(
        "ix_generation_reviews_decision",
        "generation_reviews",
        ["decision"],
    )


def downgrade() -> None:
    op.drop_index("ix_generation_reviews_decision", table_name="generation_reviews")
    op.drop_index(
        "ix_generation_reviews_reviewer_user_id", table_name="generation_reviews"
    )
    op.drop_index(
        "ix_generation_reviews_generation_job_id", table_name="generation_reviews"
    )
    op.drop_index(
        "ix_generation_reviews_organization_id", table_name="generation_reviews"
    )
    op.drop_table("generation_reviews")
