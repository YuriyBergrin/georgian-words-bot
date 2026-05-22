from sqlalchemy import select
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

