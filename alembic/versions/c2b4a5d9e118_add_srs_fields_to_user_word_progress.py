"""add srs fields to user word progress

Revision ID: c2b4a5d9e118
Revises: 1f3c9d7b2a11
Create Date: 2026-05-22 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2b4a5d9e118"
down_revision = "1f3c9d7b2a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_word_progress",
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_word_progress",
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_word_progress", "next_review_at")
    op.drop_column("user_word_progress", "level")
