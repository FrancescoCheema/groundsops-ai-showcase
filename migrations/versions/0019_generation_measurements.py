"""persist generation mask measurements

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("measurement_method", sa.String(30)))
    op.add_column("generation_jobs", sa.Column("selected_pixel_count", sa.Integer()))
    op.add_column("generation_jobs", sa.Column("total_pixel_count", sa.Integer()))
    op.add_column(
        "generation_jobs", sa.Column("calibration_pixel_length", sa.Numeric(12, 4))
    )
    op.add_column(
        "generation_jobs", sa.Column("calibration_real_length", sa.Numeric(12, 4))
    )
    op.add_column("generation_jobs", sa.Column("calibration_unit", sa.String(10)))
    op.add_column("generation_jobs", sa.Column("estimated_area", sa.Numeric(14, 4)))
    op.add_column("generation_jobs", sa.Column("estimated_perimeter", sa.Numeric(14, 4)))
    op.add_column(
        "generation_jobs", sa.Column("measurement_confidence", sa.String(30))
    )


def downgrade() -> None:
    for column in (
        "measurement_confidence",
        "estimated_perimeter",
        "estimated_area",
        "calibration_unit",
        "calibration_real_length",
        "calibration_pixel_length",
        "total_pixel_count",
        "selected_pixel_count",
        "measurement_method",
    ):
        op.drop_column("generation_jobs", column)
