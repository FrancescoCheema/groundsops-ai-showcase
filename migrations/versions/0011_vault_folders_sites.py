"""add persistent vault folders and sites

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vault_folders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["organization_users.id"]),
    )
    op.create_index("ix_vault_folders_organization_id", "vault_folders", ["organization_id"])
    op.create_index("ix_vault_folders_created_by_user_id", "vault_folders", ["created_by_user_id"])
    op.create_table(
        "vault_sites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["organization_users.id"]),
    )
    op.create_index("ix_vault_sites_organization_id", "vault_sites", ["organization_id"])
    op.create_index(
        "ix_vault_sites_created_by_user_id", "vault_sites", ["created_by_user_id"]
    )
    op.add_column("vault_files", sa.Column("folder_id", sa.String(36), nullable=True))
    op.add_column("vault_files", sa.Column("site_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_vault_files_folder", "vault_files", "vault_folders", ["folder_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_vault_files_site", "vault_files", "vault_sites", ["site_id"], ["id"]
    )
    op.create_index("ix_vault_files_folder_id", "vault_files", ["folder_id"])
    op.create_index("ix_vault_files_site_id", "vault_files", ["site_id"])


def downgrade() -> None:
    op.drop_constraint("fk_vault_files_site", "vault_files", type_="foreignkey")
    op.drop_constraint("fk_vault_files_folder", "vault_files", type_="foreignkey")
    op.drop_column("vault_files", "site_id")
    op.drop_column("vault_files", "folder_id")
    op.drop_table("vault_sites")
    op.drop_table("vault_folders")
