from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.word import Word


class TopicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name_exact(self, name: str) -> Topic | None:
        result = await self.session.execute(select(Topic).where(Topic.name == name))
        return result.scalar_one_or_none()

    async def get_by_name_casefold(self, name: str) -> Topic | None:
        result = await self.session.execute(select(Topic).where(func.lower(Topic.name) == name.lower()).limit(1))
        return result.scalar_one_or_none()

    async def get_or_create_topic_id(self, topic_name: str) -> int | None:
        if topic_name == "-":
            return None
        normalized_topic_name = topic_name.strip()
        topic = await self.get_by_name_casefold(normalized_topic_name)
        if topic is None:
            topic = Topic(name=normalized_topic_name)
            self.session.add(topic)
            await self.session.flush()
        return topic.id

    async def list_topics_with_words(self) -> list[str]:
        result = await self.session.execute(
            select(Topic.name).join(Word, Word.topic_id == Topic.id).distinct().order_by(Topic.name)
        )
        return list(result.scalars().all())

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

    async def get_topic_name_for_word(self, georgian: str) -> str | None:
        result = await self.session.execute(
            select(Topic.name)
            .select_from(Word)
            .outerjoin(Topic, Word.topic_id == Topic.id)
            .where(Word.georgian == georgian)
        )
        return result.scalar_one_or_none()

    async def delete_topic_with_words(self, topic_name: str) -> int | None:
        topic = await self.get_by_name_casefold(topic_name)
        if topic is None:
            return None
        deleted_words_result = await self.session.execute(delete(Word).where(Word.topic_id == topic.id))
        await self.session.delete(topic)
        return deleted_words_result.rowcount or 0

    async def cleanup_unused_topics(self) -> None:
        await self.session.execute(delete(Topic).where(~exists(select(Word.id).where(Word.topic_id == Topic.id))))
