"""persist company branding, invoices and timesheets

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("logo_storage_key", sa.String(500)))
    op.add_column("organizations", sa.Column("logo_media_type", sa.String(50)))
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.String(36), nullable=False),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.UniqueConstraint("organization_id", "number", name="uq_invoice_org_number"),
    )
    op.create_index("ix_invoices_organization_id", "invoices", ["organization_id"])
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_table(
        "timesheet_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("property_id", sa.String(36)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["organization_users.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
    )
    op.create_index(
        "ix_timesheet_entries_organization_id",
        "timesheet_entries",
        ["organization_id"],
    )
    op.create_index("ix_timesheet_entries_user_id", "timesheet_entries", ["user_id"])
    op.create_index("ix_timesheet_entries_property_id", "timesheet_entries", ["property_id"])


def downgrade() -> None:
    op.drop_table("timesheet_entries")
    op.drop_table("invoices")
    op.drop_column("organizations", "logo_media_type")
    op.drop_column("organizations", "logo_storage_key")
