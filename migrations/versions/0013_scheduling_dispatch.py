"""add persistent scheduling and dispatch fields

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_orders", sa.Column("assigned_user_id", sa.String(36)))
    op.add_column("work_orders", sa.Column("scheduled_start", sa.DateTime(timezone=True)))
    op.add_column("work_orders", sa.Column("scheduled_end", sa.DateTime(timezone=True)))
    op.add_column(
        "work_orders",
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
    )
    op.create_foreign_key(
        "fk_work_orders_assigned_user",
        "work_orders",
        "organization_users",
        ["assigned_user_id"],
        ["id"],
    )
    op.create_index("ix_work_orders_assigned_user_id", "work_orders", ["assigned_user_id"])
    op.create_index("ix_work_orders_scheduled_start", "work_orders", ["scheduled_start"])


def downgrade() -> None:
    op.drop_constraint("fk_work_orders_assigned_user", "work_orders", type_="foreignkey")
    op.drop_column("work_orders", "priority")
    op.drop_column("work_orders", "scheduled_end")
    op.drop_column("work_orders", "scheduled_start")
    op.drop_column("work_orders", "assigned_user_id")
