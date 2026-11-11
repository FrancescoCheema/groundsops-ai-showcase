"""Add job completion costs and invoice payments.

Revision ID: 0023_job_completion_payments
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0023_job_completion_payments"
down_revision = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_orders", sa.Column("actual_labour_hours", sa.Numeric(10, 2)))
    op.add_column("work_orders", sa.Column("actual_labour_rate", sa.Numeric(12, 2)))
    op.add_column("work_orders", sa.Column("actual_materials", sa.JSON()))
    op.add_column("work_orders", sa.Column("actual_total", sa.Numeric(12, 2)))
    op.add_column("work_orders", sa.Column("completion_notes", sa.Text()))
    op.add_column("work_orders", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("invoices", sa.Column("work_order_id", sa.String(36)))
    op.add_column(
        "invoices",
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_invoices_work_order_id",
        "invoices",
        "work_orders",
        ["work_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_invoices_work_order_id", "invoices", ["work_order_id"])
    op.create_table(
        "invoice_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("invoice_id", sa.String(36), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(200)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_invoice_payments_organization_id", "invoice_payments", ["organization_id"])
    op.create_index("ix_invoice_payments_invoice_id", "invoice_payments", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("invoice_payments")
    op.drop_constraint("uq_invoices_work_order_id", "invoices", type_="unique")
    op.drop_constraint("fk_invoices_work_order_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "paid_amount")
    op.drop_column("invoices", "work_order_id")
    for column in (
        "completed_at",
        "completion_notes",
        "actual_total",
        "actual_materials",
        "actual_labour_rate",
        "actual_labour_hours",
    ):
        op.drop_column("work_orders", column)
