from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.user_word_progress import UserWordProgress
from app.models.word import Word


class TrainingSchedulingService:
    def __init__(self, session: AsyncSession):
        self.session = session

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

