from sqlalchemy import func, or_, select
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

    async def bulk_import_from_text(self, payload: str, dry_run: bool = False) -> dict[str, int | list[str]]:
        added = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        for idx, raw_line in enumerate(payload.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                errors.append(f"Строка {idx}: нужно минимум 2 колонки (georgian | russian | topic)")
                continue

            georgian = parts[0]
            russian = parts[1]
            topic_name = parts[2] if len(parts) >= 3 and parts[2] else "-"

            if not georgian or not russian:
                errors.append(f"Строка {idx}: пустое слово или перевод")
                continue

            word_result = await self.session.execute(select(Word).where(Word.georgian == georgian))
            word = word_result.scalar_one_or_none()
            topic_id = await self._get_or_create_topic_id(topic_name)

            if word is None:
                self.session.add(Word(georgian=georgian, russian=russian, topic_id=topic_id))
                added += 1
            else:
                changed = False
                if word.russian != russian:
                    word.russian = russian
                    changed = True
                if word.topic_id != topic_id:
                    word.topic_id = topic_id
                    changed = True
                if changed:
                    updated += 1
                else:
                    skipped += 1

        if dry_run:
            await self.session.rollback()
        else:
            await self.session.commit()
        return {"added": added, "updated": updated, "skipped": skipped, "errors_count": len(errors), "errors": errors}

    async def update_word(self, georgian: str, new_russian: str, new_topic_name: str) -> bool:
        word_result = await self.session.execute(select(Word).where(Word.georgian == georgian))
        word = word_result.scalar_one_or_none()
        if word is None:
            return False

        word.russian = new_russian
        word.topic_id = await self._get_or_create_topic_id(new_topic_name)
        await self.session.commit()
        return True

    async def get_word_topic_name(self, georgian: str) -> str | None:
        result = await self.session.execute(
            select(Topic.name).select_from(Word).outerjoin(Topic, Word.topic_id == Topic.id).where(Word.georgian == georgian)
        )
        return result.scalar_one_or_none()

    async def word_exists(self, georgian: str) -> bool:
        result = await self.session.execute(select(Word.id).where(Word.georgian == georgian).limit(1))
        return result.scalar_one_or_none() is not None

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

    async def delete_word(self, georgian: str) -> bool:
        word_result = await self.session.execute(select(Word).where(Word.georgian == georgian))
        word = word_result.scalar_one_or_none()
        if word is None:
            return False
        await self.session.delete(word)
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
