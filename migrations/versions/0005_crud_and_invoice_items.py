"""add normalized invoice line items

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("invoice_id", sa.String(36), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])
    connection = op.get_bind()
    invoices = connection.execute(
        sa.text("SELECT id, description, quantity, rate, subtotal FROM invoices")
    ).mappings()
    for invoice in invoices:
        connection.execute(
            sa.text(
                "INSERT INTO invoice_items "
                "(id, invoice_id, description, quantity, rate, line_total, position) "
                "VALUES (:id, :invoice_id, :description, :quantity, :rate, :total, 0)"
            ),
            {
                "id": str(uuid4()),
                "invoice_id": invoice["id"],
                "description": invoice["description"],
                "quantity": invoice["quantity"],
                "rate": invoice["rate"],
                "total": invoice["subtotal"],
            },
        )


def downgrade() -> None:
    op.drop_index("ix_invoice_items_invoice_id", table_name="invoice_items")
    op.drop_table("invoice_items")
