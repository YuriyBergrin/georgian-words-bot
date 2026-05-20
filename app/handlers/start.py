from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.redis import get_redis
from app.db.session import SessionLocal
from app.keyboards.main_menu import main_menu
from app.services.user_service import UserService

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    async with SessionLocal() as session:
        service = UserService(session)
        await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

    redis = get_redis()
    await redis.incr(f"user:{message.from_user.id}:starts")

    await message.answer(
        "Привет! Я бот для изучения грузинских слов. Начнем учить სიტყვები!",
        reply_markup=main_menu,
    )
