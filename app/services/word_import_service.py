from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.word import Word


class WordImportService:
    def __init__(self, session: AsyncSession):
        self.session = session

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
            await self._cleanup_unused_topics()
            await self.session.commit()
        return {"added": added, "updated": updated, "skipped": skipped, "errors_count": len(errors), "errors": errors}

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
