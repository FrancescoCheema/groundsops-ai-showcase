"""add invoice branding, tax, and recipient snapshots

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("invoice_logo_storage_key", sa.String(500)))
    op.add_column("organizations", sa.Column("invoice_logo_media_type", sa.String(50)))
    op.add_column("customers", sa.Column("address", sa.String(500)))
    op.alter_column("invoices", "customer_id", existing_type=sa.String(36), nullable=True)
    for name, length in (
        ("customer_name", 200),
        ("customer_email", 320),
        ("customer_phone", 40),
        ("customer_address", 500),
        ("company_email", 320),
        ("company_phone", 40),
        ("company_address", 500),
    ):
        op.add_column("invoices", sa.Column(name, sa.String(length)))
    for name, precision in (
        ("gst_rate", sa.Numeric(6, 3)),
        ("pst_rate", sa.Numeric(6, 3)),
        ("gst_amount", sa.Numeric(12, 2)),
        ("pst_amount", sa.Numeric(12, 2)),
        ("total", sa.Numeric(12, 2)),
    ):
        op.add_column(
            "invoices",
            sa.Column(name, precision, nullable=False, server_default="0"),
        )
    op.execute("UPDATE invoices SET total = subtotal")


def downgrade() -> None:
    for name in ("total", "pst_amount", "gst_amount", "pst_rate", "gst_rate"):
        op.drop_column("invoices", name)
    for name in (
        "company_address",
        "company_phone",
        "company_email",
        "customer_address",
        "customer_phone",
        "customer_email",
        "customer_name",
    ):
        op.drop_column("invoices", name)
    op.alter_column("invoices", "customer_id", existing_type=sa.String(36), nullable=False)
    op.drop_column("customers", "address")
    op.drop_column("organizations", "invoice_logo_media_type")
    op.drop_column("organizations", "invoice_logo_storage_key")
