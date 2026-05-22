"""add streak_correct to progress

Revision ID: 8b2e1df4c6a9
Revises: 7a1d3f6e4b20
Create Date: 2026-05-22 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b2e1df4c6a9"
down_revision = "7a1d3f6e4b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_word_progress",
        sa.Column("streak_correct", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE user_word_progress SET streak_correct = 0 WHERE streak_correct IS NULL")


def downgrade() -> None:
    op.drop_column("user_word_progress", "streak_correct")
