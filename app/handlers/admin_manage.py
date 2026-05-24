from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.db.session import SessionLocal
from app.services.admin_service import AdminService

router = Router()


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
