from pathlib import Path

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from app.db.redis import get_redis
from app.db.session import SessionLocal
from app.handlers.common_helpers import is_admin_user
from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import AdminService
from app.services.user_service import UserService

router = Router()
HELP_TEXT_PATH = Path(__file__).resolve().parent.parent / "help.txt"


def get_help_text() -> str:
    return HELP_TEXT_PATH.read_text(encoding="utf-8")


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    async with SessionLocal() as session:
        service = UserService(session)
        user = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await service.touch_daily_streak(user)
        await session.commit()

    redis = get_redis()
    await redis.incr(f"user:{message.from_user.id}:starts")

    await message.answer(
        "Привет! Я бот для изучения грузинских слов. Начнем учить სიტყვები!",
        reply_markup=get_main_menu(await is_admin_user(message.from_user.id)),
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(get_help_text())


@router.message(Command("admins"))
async def admins_list_handler(message: Message) -> None:
    if not AdminService.is_bootstrap_admin(message.from_user.id):
        await message.answer("Команда доступна только bootstrap-суперадмину.")
        return

    async with SessionLocal() as session:
        ids = await AdminService(session).list_admin_ids()

    lines = ["Текущие админы:"]
    lines.extend(f"- {admin_id}" for admin_id in ids)
    await message.answer("\n".join(lines))


@router.message(Command("add_admin"))
async def add_admin_handler(message: Message, command: CommandObject) -> None:
    if not AdminService.is_bootstrap_admin(message.from_user.id):
        await message.answer("Команда доступна только bootstrap-суперадмину.")
        return

    if not command.args:
        await message.answer("Использование: /add_admin <telegram_id>")
        return

    try:
        telegram_id = int(command.args.strip())
    except ValueError:
        await message.answer("telegram_id должен быть числом.")
        return

    async with SessionLocal() as session:
        service = AdminService(session)
        created = await service.add_admin(telegram_id)
        if created:
            await session.commit()

    if created:
        await message.answer(f"Админ добавлен: {telegram_id}")
    else:
        await message.answer("Этот пользователь уже админ.")


@router.message(Command("remove_admin"))
async def remove_admin_handler(message: Message, command: CommandObject) -> None:
    if not AdminService.is_bootstrap_admin(message.from_user.id):
        await message.answer("Команда доступна только bootstrap-суперадмину.")
        return

    if not command.args:
        await message.answer("Использование: /remove_admin <telegram_id>")
        return

    try:
        telegram_id = int(command.args.strip())
    except ValueError:
        await message.answer("telegram_id должен быть числом.")
        return

    async with SessionLocal() as session:
        service = AdminService(session)
        removed, reason = await service.remove_admin(telegram_id)
        if removed:
            await session.commit()

    if removed:
        await message.answer(f"Админ удален: {telegram_id}")
    else:
        await message.answer(reason or "Не удалось удалить админа.")
