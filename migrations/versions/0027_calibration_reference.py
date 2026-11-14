"""Record the known object used to measure a generation.

Revision ID: 0027_calibration_reference
Revises: 0026_price_list
"""

import sqlalchemy as sa
from alembic import op

revision = "0027_calibration_reference"
down_revision = "0026_price_list"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs", sa.Column("calibration_reference", sa.String(80), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "calibration_reference")
