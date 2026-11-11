"""add folder and site controls

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("vault_folders", "vault_sites"):
        op.add_column(
            table,
            sa.Column(
                "access_scope",
                sa.String(20),
                nullable=False,
                server_default="organization",
            ),
        )
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_table(
        "vault_container_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("container_type", sa.String(10), nullable=False),
        sa.Column("container_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["organization_users.id"]),
    )
    op.create_index(
        "ix_vault_container_shares_container_id",
        "vault_container_shares",
        ["container_id"],
    )
    op.create_index(
        "ix_vault_container_shares_token_hash",
        "vault_container_shares",
        ["token_hash"],
    )


def downgrade() -> None:
    op.drop_table("vault_container_shares")
    for table in ("vault_sites", "vault_folders"):
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "access_scope")
