"""add admins table

Revision ID: 5b7a9c2d1e4f
Revises: e1a9c4b7d2f0
Create Date: 2026-05-24 18:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b7a9c2d1e4f"
down_revision: str | None = "e1a9c4b7d2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admins_telegram_id"), "admins", ["telegram_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_admins_telegram_id"), table_name="admins")
    op.drop_table("admins")
