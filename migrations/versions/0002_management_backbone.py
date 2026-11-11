"""Add users, customers, materials, designs, and quotes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_organization_users_organization_id", "organization_users", ["organization_id"]
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])
    with op.batch_alter_table("properties") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key("fk_properties_customer", "customers", ["customer_id"], ["id"])
        batch_op.create_index("ix_properties_customer_id", ["customer_id"])
    op.create_table(
        "materials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_materials_organization_id", "materials", ["organization_id"])
    op.create_table(
        "material_variants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("material_id", sa.String(36), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("colour", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("default_waste_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_material_variants_organization_id", "material_variants", ["organization_id"]
    )
    op.create_index("ix_material_variants_material_id", "material_variants", ["material_id"])
    op.create_table(
        "design_projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("property_id", sa.String(36), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_design_projects_organization_id", "design_projects", ["organization_id"])
    op.create_index("ix_design_projects_property_id", "design_projects", ["property_id"])
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column(
            "design_project_id",
            sa.String(36),
            sa.ForeignKey("design_projects.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("assumptions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quotes_organization_id", "quotes", ["organization_id"])
    op.create_index("ix_quotes_design_project_id", "quotes", ["design_project_id"])


def downgrade() -> None:
    op.drop_table("quotes")
    op.drop_table("design_projects")
    op.drop_table("material_variants")
    op.drop_table("materials")
    with op.batch_alter_table("properties") as batch_op:
        batch_op.drop_index("ix_properties_customer_id")
        batch_op.drop_constraint("fk_properties_customer", type_="foreignkey")
        batch_op.drop_column("customer_id")
    op.drop_table("customers")
    op.drop_table("organization_users")
