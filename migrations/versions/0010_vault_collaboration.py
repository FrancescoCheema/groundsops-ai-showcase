"""add secure vault collaboration and recycle bin

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vault_files",
        sa.Column("access_scope", sa.String(20), nullable=False, server_default="organization"),
    )
    op.add_column(
        "vault_files", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "vault_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["vault_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["organization_users.id"]),
    )
    op.create_index("ix_vault_shares_file_id", "vault_shares", ["file_id"])
    op.create_index(
        "ix_vault_shares_organization_id", "vault_shares", ["organization_id"]
    )
    op.create_index(
        "ix_vault_shares_created_by_user_id", "vault_shares", ["created_by_user_id"]
    )
    op.create_index("ix_vault_shares_token_hash", "vault_shares", ["token_hash"])


def downgrade() -> None:
    op.drop_table("vault_shares")
    op.drop_column("vault_files", "deleted_at")
    op.drop_column("vault_files", "access_scope")
