from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.word import Word


class TopicService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_topics_with_words(self) -> list[str]:
        topics_result = await self.session.execute(
            select(Topic.name).join(Word, Word.topic_id == Topic.id).distinct().order_by(Topic.name)
        )
        return list(topics_result.scalars().all())

    async def topic_exists_with_words(self, topic_name: str) -> bool:
        result = await self.session.execute(
            select(Topic.id)
            .join(Word, Word.topic_id == Topic.id)
            .where(func.lower(Topic.name) == topic_name.lower())
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_topic_words(self, topic_name: str) -> list[tuple[str, str]]:
        result = await self.session.execute(
            select(Word.georgian, Word.russian)
            .select_from(Word)
            .join(Topic, Word.topic_id == Topic.id)
            .where(func.lower(Topic.name) == topic_name.lower())
            .order_by(Word.georgian.asc())
        )
        return [(georgian, russian) for georgian, russian in result.all()]
