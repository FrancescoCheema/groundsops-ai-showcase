"""Link approved quotes to scheduled work orders."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("work_orders") as batch_op:
        batch_op.add_column(sa.Column("quote_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("design_project_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("quoted_total", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("quote_currency", sa.String(3), nullable=True))
        batch_op.add_column(sa.Column("material_checklist", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("customer_instructions", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_work_orders_quote",
            "quotes",
            ["quote_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_work_orders_design_project",
            "design_projects",
            ["design_project_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint("uq_work_order_quote_id", ["quote_id"])
        batch_op.create_index("ix_work_orders_quote_id", ["quote_id"])
        batch_op.create_index("ix_work_orders_design_project_id", ["design_project_id"])


def downgrade() -> None:
    with op.batch_alter_table("work_orders") as batch_op:
        batch_op.drop_index("ix_work_orders_design_project_id")
        batch_op.drop_index("ix_work_orders_quote_id")
        batch_op.drop_constraint("uq_work_order_quote_id", type_="unique")
        batch_op.drop_constraint("fk_work_orders_design_project", type_="foreignkey")
        batch_op.drop_constraint("fk_work_orders_quote", type_="foreignkey")
        batch_op.drop_column("customer_instructions")
        batch_op.drop_column("material_checklist")
        batch_op.drop_column("quote_currency")
        batch_op.drop_column("quoted_total")
        batch_op.drop_column("design_project_id")
        batch_op.drop_column("quote_id")
