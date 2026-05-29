from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.word import Word


class WordService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_word(self, georgian: str, russian: str, topic_name: str) -> bool:
        existing_result = await self.session.execute(select(Word).where(Word.georgian == georgian))
        existing_word = existing_result.scalar_one_or_none()
        if existing_word is not None:
            return False

        topic = None
        if topic_name != "-":
            topic_result = await self.session.execute(select(Topic).where(Topic.name == topic_name))
            topic = topic_result.scalar_one_or_none()
            if topic is None:
                topic = Topic(name=topic_name)
                self.session.add(topic)
                await self.session.flush()

        self.session.add(Word(georgian=georgian, russian=russian, topic_id=topic.id if topic else None))
        await self.session.commit()
        return True

    async def update_word(
        self, georgian: str, new_georgian: str, new_russian: str, new_topic_name: str
    ) -> str:
        word_result = await self.session.execute(select(Word).where(Word.georgian == georgian))
        word = word_result.scalar_one_or_none()
        if word is None:
            return "not_found"

        if new_georgian != georgian:
            existing_result = await self.session.execute(select(Word.id).where(Word.georgian == new_georgian).limit(1))
            existing_word_id = existing_result.scalar_one_or_none()
            if existing_word_id is not None:
                return "duplicate"

        word.georgian = new_georgian
        word.russian = new_russian
        word.topic_id = await self._get_or_create_topic_id(new_topic_name)
        await self._cleanup_unused_topics()
        await self.session.commit()
        return "updated"

    async def get_word_topic_name(self, georgian: str) -> str | None:
        result = await self.session.execute(
            select(Topic.name).select_from(Word).outerjoin(Topic, Word.topic_id == Topic.id).where(Word.georgian == georgian)
        )
        return result.scalar_one_or_none()

    async def word_exists(self, georgian: str) -> bool:
        result = await self.session.execute(select(Word.id).where(Word.georgian == georgian).limit(1))
        return result.scalar_one_or_none() is not None

    async def delete_word(self, georgian: str) -> bool:
        word_result = await self.session.execute(select(Word).where(Word.georgian == georgian))
        word = word_result.scalar_one_or_none()
        if word is None:
            return False
        await self.session.delete(word)
        await self._cleanup_unused_topics()
        await self.session.commit()
        return True

    async def _get_or_create_topic_id(self, topic_name: str) -> int | None:
        if topic_name == "-":
            return None
        normalized_topic_name = topic_name.strip()
        topic_result = await self.session.execute(
            select(Topic).where(func.lower(Topic.name) == normalized_topic_name.lower())
        )
        topic = topic_result.scalar_one_or_none()
        if topic is None:
            topic = Topic(name=normalized_topic_name)
            self.session.add(topic)
            await self.session.flush()
        return topic.id

    async def _cleanup_unused_topics(self) -> None:
        await self.session.execute(
            delete(Topic).where(
                ~exists(select(Word.id).where(Word.topic_id == Topic.id))
            )
        )
