import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from app.config.settings import settings
from app.db.redis import close_redis, get_redis, init_redis
from app.handlers import router as app_router


async def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    bot = Bot(token=settings.bot_token)
    await init_redis()
    redis = get_redis()
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
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
