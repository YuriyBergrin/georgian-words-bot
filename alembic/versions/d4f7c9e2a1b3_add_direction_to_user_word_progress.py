"""add direction to user_word_progress

Revision ID: d4f7c9e2a1b3
Revises: 8b2e1df4c6a9
Create Date: 2026-05-22 14:40:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4f7c9e2a1b3"
down_revision = "8b2e1df4c6a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_word_progress",
        sa.Column("direction", sa.String(length=10), nullable=False, server_default="ge_ru"),
    )
    op.drop_constraint("uq_user_word", "user_word_progress", type_="unique")
    op.create_unique_constraint("uq_user_word_direction", "user_word_progress", ["user_id", "word_id", "direction"])


def downgrade() -> None:
    op.drop_constraint("uq_user_word_direction", "user_word_progress", type_="unique")
    op.create_unique_constraint("uq_user_word", "user_word_progress", ["user_id", "word_id"])
    op.drop_column("user_word_progress", "direction")
