from app.infrastructure.db.uow import UnitOfWork
from app.services.stats_service import StatsService


class CommonService:
    async def get_user_stats(self, telegram_id: int) -> dict[str, int]:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            return await StatsService(uow.session).get_user_stats(telegram_id)

    async def list_topics_with_words(self) -> list[str]:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            return await uow.topics.list_topics_with_words()

    async def topic_exists_with_words(self, topic_name: str) -> bool:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            return await uow.topics.topic_exists_with_words(topic_name)

    async def get_topic_words(self, topic_name: str) -> list[tuple[str, str]]:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            return await uow.topics.get_topic_words(topic_name)

    async def delete_topic_with_words(self, topic_name: str) -> int | None:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            deleted_words = await uow.topics.delete_topic_with_words(topic_name)
            if deleted_words is None:
                return None
            await uow.commit()
            return deleted_words
