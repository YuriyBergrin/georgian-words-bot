from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_word_progress import UserWordProgress
from app.models.word import Word


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_stats(self, telegram_id: int) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        total_words_result = await self.session.execute(select(func.count(Word.id)))
        total_words = total_words_result.scalar_one()

        user_result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            return {
                "total_words": total_words,
                "trained_words": 0,
                "due_words": 0,
                "total_correct": 0,
                "total_wrong": 0,
                "streak_days": 0,
            }

        trained_words_result = await self.session.execute(
            select(func.count(func.distinct(UserWordProgress.word_id))).where(UserWordProgress.user_id == user.id)
        )
        trained_words = trained_words_result.scalar_one()

        due_words_result = await self.session.execute(
            select(func.count(func.distinct(Word.id)))
            .select_from(Word)
            .outerjoin(
                UserWordProgress,
                and_(
                    UserWordProgress.word_id == Word.id,
                    UserWordProgress.user_id == user.id,
                ),
            )
            .where(
                or_(
                    UserWordProgress.next_review_at.is_(None),
                    UserWordProgress.next_review_at <= now,
                )
            )
        )
        due_words = due_words_result.scalar_one()

        answers_result = await self.session.execute(
            select(
                func.coalesce(func.sum(UserWordProgress.correct_count), 0),
                func.coalesce(func.sum(UserWordProgress.wrong_count), 0),
            ).where(UserWordProgress.user_id == user.id)
        )
        total_correct, total_wrong = answers_result.one()

        return {
            "total_words": total_words,
            "trained_words": trained_words,
            "due_words": due_words,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "streak_days": user.streak_days or 0,
        }

    async def get_hard_words(self, limit: int = 10) -> list[tuple[str, str, int, int]]:
        result = await self.session.execute(
            select(
                Word.georgian,
                Word.russian,
                func.coalesce(func.sum(UserWordProgress.wrong_count), 0).label("wrong_sum"),
                func.coalesce(func.sum(UserWordProgress.correct_count), 0).label("correct_sum"),
            )
            .join(UserWordProgress, UserWordProgress.word_id == Word.id)
            .group_by(Word.id, Word.georgian, Word.russian)
            .having(func.coalesce(func.sum(UserWordProgress.wrong_count), 0) > 0)
            .order_by(func.coalesce(func.sum(UserWordProgress.wrong_count), 0).desc(), Word.georgian.asc())
            .limit(limit)
        )
        return [(g, r, w, c) for g, r, w, c in result.all()]
