from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.user import User
from app.models.user_word_progress import UserWordProgress
from app.models.word import Word


class TrainingService:
    DIRECTION_GE_RU = "ge_ru"
    DIRECTION_RU_GE = "ru_ge"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        user_result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()
        if user is not None:
            return user

        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        self.session.add(user)
        await self.session.flush()
        return user

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
            query = query.join(Topic, Word.topic_id == Topic.id).where(Topic.name == topic)
        if exclude_word_id is not None:
            query = query.where(Word.id != exclude_word_id)

        result = await self.session.execute(query.order_by(func.random()).limit(1))
        return result.scalar_one_or_none()

    async def get_random_word_with_direction(
        self, user_id: int, topic: str | None = None, exclude_word_id: int | None = None
    ) -> tuple[Word, str] | None:
        directions = [self.DIRECTION_GE_RU, self.DIRECTION_RU_GE]
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
        if direction == self.DIRECTION_RU_GE:
            return word.russian, word.georgian
        return word.georgian, word.russian

    async def build_translation_options(self, correct_answer: str, word_id: int, answer_language: str) -> list[str]:
        column = Word.russian if answer_language == "russian" else Word.georgian
        result = await self.session.execute(select(column).where(Word.id != word_id).order_by(func.random()).limit(3))
        distractors = list(result.scalars().all())
        options = [correct_answer, *distractors]
        random.shuffle(options)
        return options

    async def apply_answer(self, user: User, word: Word, direction: str, is_correct: bool, is_choice: bool) -> None:
        now = datetime.now(timezone.utc)
        progress_result = await self.session.execute(
            select(UserWordProgress).where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.word_id == word.id,
                UserWordProgress.direction == direction,
            )
        )
        progress = progress_result.scalar_one_or_none()
        if progress is None:
            progress = UserWordProgress(
                user_id=user.id,
                word_id=word.id,
                direction=direction,
                correct_count=0,
                wrong_count=0,
                streak_correct=0,
                level=0,
            )
            self.session.add(progress)

        progress.correct_count = progress.correct_count or 0
        progress.wrong_count = progress.wrong_count or 0
        progress.streak_correct = progress.streak_correct or 0
        progress.level = progress.level or 0

        if is_correct:
            progress.correct_count += 1
            current_level = progress.level
            if not is_choice:
                progress.streak_correct += 1

            needed_streak = self._needed_streak_for_level(current_level)
            if progress.streak_correct >= needed_streak:
                progress.level = current_level + 1
                progress.streak_correct = 0
                progress.next_review_at = now + timedelta(days=self._interval_days_for_level(current_level))
            else:
                progress.next_review_at = now + timedelta(minutes=10)
        else:
            progress.wrong_count += 1
            progress.streak_correct = 0
            progress.level = max(progress.level - 1, 0)
            progress.next_review_at = now

        progress.last_answered_at = now

    @staticmethod
    def _needed_streak_for_level(level: int) -> int:
        if level in (0, 1):
            return 2
        if level in (2, 3):
            return 3
        return 4

    @staticmethod
    def _interval_days_for_level(level: int) -> int:
        if level == 0:
            return 1
        if level == 1:
            return 3
        if level == 2:
            return 7
        if level == 3:
            return 14
        return 30

    async def reset_topic_for_repeat(self, user_id: int, topic: str) -> None:
        now = datetime.now(timezone.utc)
        word_ids_subquery = select(Word.id).join(Topic, Word.topic_id == Topic.id).where(Topic.name == topic)
        await self.session.execute(
            update(UserWordProgress)
            .where(
                UserWordProgress.user_id == user_id,
                UserWordProgress.word_id.in_(word_ids_subquery),
            )
            .values(next_review_at=now)
        )
