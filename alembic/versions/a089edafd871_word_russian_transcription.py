"""word russian transcription

Revision ID: a089edafd871
Revises: 5963077ef67e
Create Date: 2026-05-20 18:43:38.508582
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'a089edafd871'
down_revision = '5963077ef67e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("words", "translation", new_column_name="russian", existing_type=sa.String(length=255))
    op.alter_column("words", "example", new_column_name="transcription", existing_type=sa.Text(), type_=sa.String(length=255))
    op.drop_index(op.f("ix_words_translation"), table_name="words")
    op.create_index(op.f("ix_words_russian"), "words", ["russian"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_words_russian"), table_name="words")
    op.create_index(op.f("ix_words_translation"), "words", ["translation"], unique=False)
    op.alter_column("words", "transcription", new_column_name="example", existing_type=sa.String(length=255), type_=sa.Text())
    op.alter_column("words", "russian", new_column_name="translation", existing_type=sa.String(length=255))
