import asyncio
import sys

from aiogram import Bot, Dispatcher
from loguru import logger

from app.config.settings import settings
from app.db.redis import close_redis, init_redis
from app.handlers import router as app_router


async def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(app_router)

    logger.info("Starting bot polling")
    await init_redis()
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Stopping bot polling")
        await close_redis()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
