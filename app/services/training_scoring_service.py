from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_word_progress import UserWordProgress
from app.models.word import Word


class TrainingScoringService:
    def __init__(self, session: AsyncSession):
        self.session = session

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

