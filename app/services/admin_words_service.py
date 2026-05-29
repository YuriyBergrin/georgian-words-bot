from app.infrastructure.db.uow import UnitOfWork
from app.contracts.admin_words_dto import EditWordContext, ImportWordsResult, SearchWordsPage


class AdminWordsService:
    async def list_topics_with_words(self) -> list[str]:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            return await uow.topics.list_topics_with_words()

    async def export_words_rows(self) -> list[tuple[str, str, str]]:
        async with UnitOfWork() as uow:
            assert uow.word_queries is not None
            return await uow.word_queries.export_words_rows()

    async def import_words(self, payload: str, dry_run: bool = False) -> ImportWordsResult:
        added = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        async with UnitOfWork() as uow:
            assert uow.words is not None
            assert uow.topics is not None
            assert uow.session is not None

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

                word = await uow.words.get_by_georgian(georgian)
                topic_id = await uow.topics.get_or_create_topic_id(topic_name)
                if word is None:
                    await uow.words.add(georgian=georgian, russian=russian, topic_id=topic_id)
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
                await uow.rollback()
            else:
                await uow.topics.cleanup_unused_topics()
                await uow.commit()

        return ImportWordsResult(
            added=added,
            updated=updated,
            skipped=skipped,
            errors_count=len(errors),
            errors=errors,
        )

    async def search_words(self, query: str, page: int, page_size: int) -> SearchWordsPage:
        async with UnitOfWork() as uow:
            assert uow.word_queries is not None
            total = await uow.word_queries.count_search_words(query)
            rows = await uow.word_queries.search_words(query=query, offset=page * page_size, limit=page_size)
            return SearchWordsPage(total=total, rows=rows)

    async def delete_word(self, georgian: str) -> bool:
        async with UnitOfWork() as uow:
            assert uow.words is not None
            assert uow.topics is not None
            word = await uow.words.get_by_georgian(georgian)
            if word is None:
                return False
            await uow.words.delete(word)
            await uow.topics.cleanup_unused_topics()
            await uow.commit()
            return True

    async def get_edit_context(self, georgian: str) -> EditWordContext:
        async with UnitOfWork() as uow:
            assert uow.words is not None
            assert uow.topics is not None
            exists = await uow.words.exists_by_georgian(georgian)
            if not exists:
                return EditWordContext(exists=False, current_topic=None)
            topic_name = await uow.topics.get_topic_name_for_word(georgian)
            return EditWordContext(exists=True, current_topic=topic_name)

    async def update_word(
        self, georgian: str, new_georgian: str, new_russian: str, new_topic_name: str
    ) -> str:
        async with UnitOfWork() as uow:
            assert uow.words is not None
            assert uow.topics is not None
            word = await uow.words.get_by_georgian(georgian)
            if word is None:
                return "not_found"

            if new_georgian != georgian:
                existing_word_id = await uow.words.find_id_by_georgian(new_georgian)
                if existing_word_id is not None:
                    return "duplicate"

            word.georgian = new_georgian
            word.russian = new_russian
            word.topic_id = await uow.topics.get_or_create_topic_id(new_topic_name)
            await uow.topics.cleanup_unused_topics()
            await uow.commit()
            return "updated"

    async def add_word(self, georgian: str, russian: str, topic_name: str) -> bool:
        async with UnitOfWork() as uow:
            assert uow.words is not None
            assert uow.topics is not None
            existing_word = await uow.words.get_by_georgian(georgian)
            if existing_word is not None:
                return False

            topic_id = await uow.topics.get_or_create_topic_id(topic_name)
            await uow.words.add(georgian=georgian, russian=russian, topic_id=topic_id)
            await uow.commit()
            return True
