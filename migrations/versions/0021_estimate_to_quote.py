"""Upgrade quotes with line items and authoritative totals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("quotes") as batch_op:
        batch_op.add_column(sa.Column("generation_job_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("number", sa.String(40), nullable=True))
        batch_op.add_column(
            sa.Column("markup_rate", sa.Numeric(6, 3), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("markup_amount", sa.Numeric(12, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("tax_rate", sa.Numeric(6, 3), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_quotes_generation_job",
            "generation_jobs",
            ["generation_job_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_quotes_generation_job_id", ["generation_job_id"])

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, organization_id, subtotal, created_at FROM quotes ORDER BY created_at, id"
        )
    ).fetchall()
    counters: dict[str, int] = {}
    for row in rows:
        counters[row.organization_id] = counters.get(row.organization_id, 0) + 1
        number = f"Q-LEGACY-{counters[row.organization_id]:04d}"
        connection.execute(
            sa.text(
                "UPDATE quotes SET number=:number, total=subtotal, "
                "updated_at=created_at WHERE id=:id"
            ),
            {"number": number, "id": row.id},
        )

    with op.batch_alter_table("quotes") as batch_op:
        batch_op.alter_column("number", nullable=False)
        batch_op.alter_column("updated_at", nullable=False)
        batch_op.create_unique_constraint("uq_quote_org_number", ["organization_id", "number"])

    op.create_table(
        "quote_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "quote_id",
            sa.String(36),
            sa.ForeignKey("quotes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_quote_items_quote_id", "quote_items", ["quote_id"])


def downgrade() -> None:
    op.drop_table("quote_items")
    with op.batch_alter_table("quotes") as batch_op:
        batch_op.drop_constraint("uq_quote_org_number", type_="unique")
        batch_op.drop_index("ix_quotes_generation_job_id")
        batch_op.drop_constraint("fk_quotes_generation_job", type_="foreignkey")
        for column in (
            "updated_at",
            "total",
            "tax_amount",
            "tax_rate",
            "discount_amount",
            "markup_amount",
            "markup_rate",
            "number",
            "generation_job_id",
        ):
            batch_op.drop_column(column)
