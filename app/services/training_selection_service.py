from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.user_word_progress import UserWordProgress
from app.models.word import Word
from app.services.training_constants import DIRECTION_GE_RU, DIRECTION_RU_GE


class TrainingSelectionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_random_word(
        self,
        user_id: int,
        topic: str | None = None,
        direction: str = DIRECTION_GE_RU,
        exclude_word_id: int | None = None,
    ) -> Word | None:
        now = datetime.now(timezone.utc)
        query = (
            select(Word)
            .outerjoin(
                UserWordProgress,
                and_(
                    UserWordProgress.word_id == Word.id,
                    UserWordProgress.user_id == user_id,
                    UserWordProgress.direction == direction,
                ),
            )
            .where(
                or_(
                    UserWordProgress.next_review_at.is_(None),
                    UserWordProgress.next_review_at <= now,
                )
            )
        )

        if topic is not None:
            query = query.join(Topic, Word.topic_id == Topic.id).where(func.lower(Topic.name) == topic.lower())
        if exclude_word_id is not None:
            query = query.where(Word.id != exclude_word_id)

        result = await self.session.execute(query.order_by(func.random()).limit(1))
        return result.scalar_one_or_none()

    async def get_random_word_with_direction(
        self, user_id: int, topic: str | None = None, exclude_word_id: int | None = None
    ) -> tuple[Word, str] | None:
        directions = [DIRECTION_GE_RU, DIRECTION_RU_GE]
        random.shuffle(directions)
        for direction in directions:
            word = await self.get_random_word(
                user_id=user_id,
                topic=topic,
                direction=direction,
                exclude_word_id=exclude_word_id,
            )
            if word is not None:
                return word, direction
        return None

    def build_question(self, word: Word, direction: str) -> tuple[str, str]:
        if direction == DIRECTION_RU_GE:
            return word.russian, word.georgian
        return word.georgian, word.russian

    async def build_translation_options(self, correct_answer: str, word_id: int, answer_language: str) -> list[str]:
        column = Word.russian if answer_language == "russian" else Word.georgian
        result = await self.session.execute(select(column).where(Word.id != word_id).order_by(func.random()).limit(3))
        distractors = list(result.scalars().all())
        options = [correct_answer, *distractors]
        random.shuffle(options)
        return options
