"""Store company contact details for quotes and invoices.

Revision ID: 0028_company_contact
Revises: 0027_calibration_reference
"""

import sqlalchemy as sa
from alembic import op

revision = "0028_company_contact"
down_revision = "0027_calibration_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("contact_email", sa.String(320), nullable=True))
    op.add_column("organizations", sa.Column("contact_phone", sa.String(40), nullable=True))
    op.add_column("organizations", sa.Column("contact_address", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "contact_address")
    op.drop_column("organizations", "contact_phone")
    op.drop_column("organizations", "contact_email")
