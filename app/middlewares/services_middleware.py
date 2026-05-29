from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware

from app.services.access_service import AccessService
from app.services.admin_manage_service import AdminManageService
from app.services.admin_stats_service import AdminStatsService
from app.services.admin_words_service import AdminWordsService
from app.services.common_service import CommonService
from app.services.training_flow_service import TrainingFlowService


@dataclass(slots=True)
class AppServices:
    access: AccessService
    admin_manage: AdminManageService
    admin_stats: AdminStatsService
    admin_words: AdminWordsService
    common: CommonService
    training_flow: TrainingFlowService


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, services: AppServices):
        super().__init__()
        self.services = services

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["services"] = self.services
        return await handler(event, data)
