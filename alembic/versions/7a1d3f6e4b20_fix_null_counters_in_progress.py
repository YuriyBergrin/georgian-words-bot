"""fix null counters in progress

Revision ID: 7a1d3f6e4b20
Revises: c2b4a5d9e118
Create Date: 2026-05-22 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a1d3f6e4b20"
down_revision = "c2b4a5d9e118"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE user_word_progress SET correct_count = 0 WHERE correct_count IS NULL")
    op.execute("UPDATE user_word_progress SET wrong_count = 0 WHERE wrong_count IS NULL")
    op.execute("UPDATE user_word_progress SET level = 0 WHERE level IS NULL")

    op.alter_column("user_word_progress", "correct_count", existing_type=sa.Integer(), nullable=False, server_default="0")
    op.alter_column("user_word_progress", "wrong_count", existing_type=sa.Integer(), nullable=False, server_default="0")
    op.alter_column("user_word_progress", "level", existing_type=sa.Integer(), nullable=False, server_default="0")


def downgrade() -> None:
    op.alter_column("user_word_progress", "level", existing_type=sa.Integer(), nullable=True, server_default=None)
    op.alter_column("user_word_progress", "wrong_count", existing_type=sa.Integer(), nullable=True, server_default=None)
    op.alter_column("user_word_progress", "correct_count", existing_type=sa.Integer(), nullable=True, server_default=None)
