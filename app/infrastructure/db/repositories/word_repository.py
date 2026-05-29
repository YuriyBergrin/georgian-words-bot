from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.word import Word


class WordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_georgian(self, georgian: str) -> Word | None:
        result = await self.session.execute(select(Word).where(Word.georgian == georgian))
        return result.scalar_one_or_none()

    async def get_by_id(self, word_id: int) -> Word | None:
        result = await self.session.execute(select(Word).where(Word.id == word_id))
        return result.scalar_one_or_none()

    async def exists_by_georgian(self, georgian: str) -> bool:
        result = await self.session.execute(select(Word.id).where(Word.georgian == georgian).limit(1))
        return result.scalar_one_or_none() is not None

    async def find_id_by_georgian(self, georgian: str) -> int | None:
        result = await self.session.execute(select(Word.id).where(Word.georgian == georgian).limit(1))
        return result.scalar_one_or_none()

    async def add(self, georgian: str, russian: str, topic_id: int | None) -> None:
        self.session.add(Word(georgian=georgian, russian=russian, topic_id=topic_id))

    async def delete(self, word: Word) -> None:
        await self.session.delete(word)
