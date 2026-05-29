from app.infrastructure.db.uow import UnitOfWork
from app.services.stats_service import StatsService


class AdminStatsService:
    async def get_hard_words(self, limit: int = 10) -> list[tuple[str, str, int, int]]:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            return await StatsService(uow.session).get_hard_words(limit=limit)
