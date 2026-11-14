"""Record tape measurements taken on site to check photo measurements.

Revision ID: 0029_site_measurements
Revises: 0028_company_contact
"""

import sqlalchemy as sa
from alembic import op

revision = "0029_site_measurements"
down_revision = "0028_company_contact"
branch_labels = None
depends_on = None

COLUMNS = (
    ("site_measured_area", sa.Numeric(14, 4)),
    ("site_measured_perimeter", sa.Numeric(14, 4)),
    ("site_measured_at", sa.DateTime(timezone=True)),
    ("site_measurement_notes", sa.String(500)),
)


def upgrade() -> None:
    for name, column_type in COLUMNS:
        op.add_column("generation_jobs", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(COLUMNS):
        op.drop_column("generation_jobs", name)
