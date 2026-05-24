"""add user streak fields

Revision ID: e1a9c4b7d2f0
Revises: d4f7c9e2a1b3
Create Date: 2026-05-24 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1a9c4b7d2f0"
down_revision = "d4f7c9e2a1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("last_active_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_active_date")
    op.drop_column("users", "streak_days")
