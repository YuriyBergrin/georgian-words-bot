from pathlib import Path

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.db.redis import get_redis
from app.db.session import SessionLocal
from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import is_admin
from app.services.user_service import UserService

router = Router()
HELP_TEXT_PATH = Path(__file__).resolve().parent.parent / "help.txt"


def get_help_text() -> str:
    return HELP_TEXT_PATH.read_text(encoding="utf-8")


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
        reply_markup=get_main_menu(is_admin(message.from_user.id)),
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(get_help_text())
