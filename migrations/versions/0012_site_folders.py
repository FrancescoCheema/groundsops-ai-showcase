"""associate vault folders with sites

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vault_folders", sa.Column("site_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_vault_folders_site", "vault_folders", "vault_sites", ["site_id"], ["id"]
    )
    op.create_index("ix_vault_folders_site_id", "vault_folders", ["site_id"])


def downgrade() -> None:
    op.drop_constraint("fk_vault_folders_site", "vault_folders", type_="foreignkey")
    op.drop_column("vault_folders", "site_id")
