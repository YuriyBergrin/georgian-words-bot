import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from app.services.access_service import AccessService
from app.services.admin_manage_service import AdminManageService
from app.services.admin_stats_service import AdminStatsService
from app.services.admin_words_service import AdminWordsService
from app.services.common_service import CommonService
from app.services.training_flow_service import TrainingFlowService
from app.config.settings import settings
from app.db.redis import close_redis, get_redis, init_redis
from app.handlers import router as app_router
from app.middlewares.services_middleware import AppServices, ServicesMiddleware


async def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    bot = Bot(token=settings.bot_token)
    await init_redis()
    redis = get_redis()
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
    services = AppServices(
        access=AccessService(),
        admin_manage=AdminManageService(),
        admin_stats=AdminStatsService(),
        admin_words=AdminWordsService(),
        common=CommonService(),
        training_flow=TrainingFlowService(),
    )
    dp.update.middleware(ServicesMiddleware(services))
    dp.include_router(app_router)

    logger.info("Starting bot polling")
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Stopping bot polling")
        await storage.close()
        await close_redis()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
