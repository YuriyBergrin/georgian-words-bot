"""update user word progress fields

Revision ID: 1f3c9d7b2a11
Revises: 069fab146520
Create Date: 2026-05-22 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f3c9d7b2a11"
down_revision = "069fab146520"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "user_word_progress",
        "correct_answers",
        new_column_name="correct_count",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "user_word_progress",
        "wrong_answers",
        new_column_name="wrong_count",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "user_word_progress",
        "last_reviewed_at",
        new_column_name="last_answered_at",
        existing_type=sa.DateTime(timezone=True),
    )
    op.drop_column("user_word_progress", "status")
    op.drop_column("user_word_progress", "created_at")
    op.drop_column("user_word_progress", "updated_at")
    op.execute("DROP TYPE IF EXISTS progress_status")


def downgrade() -> None:
    progress_status = sa.Enum("NEW", "LEARNING", "KNOWN", name="progress_status")
    progress_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "user_word_progress",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "user_word_progress",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "user_word_progress",
        sa.Column("status", progress_status, server_default="NEW", nullable=False),
    )
    op.alter_column(
        "user_word_progress",
        "correct_count",
        new_column_name="correct_answers",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "user_word_progress",
        "wrong_count",
        new_column_name="wrong_answers",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "user_word_progress",
        "last_answered_at",
        new_column_name="last_reviewed_at",
        existing_type=sa.DateTime(timezone=True),
    )
