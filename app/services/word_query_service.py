from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.word import Word


class WordQueryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_words(self, query: str, offset: int, limit: int) -> list[tuple[str, str, str | None]]:
        pattern = f"%{query.strip()}%"
        result = await self.session.execute(
            select(Word.georgian, Word.russian, Topic.name)
            .select_from(Word)
            .outerjoin(Topic, Word.topic_id == Topic.id)
            .where(
                or_(
                    Word.georgian.ilike(pattern),
                    Word.russian.ilike(pattern),
                    Topic.name.ilike(pattern),
                )
            )
            .order_by(Word.georgian.asc())
            .offset(offset)
            .limit(limit)
        )
        return [(g, r, t) for g, r, t in result.all()]

    async def count_search_words(self, query: str) -> int:
        pattern = f"%{query.strip()}%"
        result = await self.session.execute(
            select(func.count(Word.id))
            .select_from(Word)
            .outerjoin(Topic, Word.topic_id == Topic.id)
            .where(
                or_(
                    Word.georgian.ilike(pattern),
                    Word.russian.ilike(pattern),
                    Topic.name.ilike(pattern),
                )
            )
        )
        return result.scalar_one()

    async def export_words_rows(self) -> list[tuple[str, str, str]]:
        result = await self.session.execute(
            select(Word.georgian, Word.russian, Topic.name)
            .select_from(Word)
            .outerjoin(Topic, Word.topic_id == Topic.id)
            .order_by(Word.georgian.asc())
        )
        rows = []
        for georgian, russian, topic_name in result.all():
            rows.append((georgian, russian, topic_name or "-"))
        return rows
