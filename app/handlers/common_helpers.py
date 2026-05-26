from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from loguru import logger

from app.db.session import SessionLocal
from app.keyboards.training import BACK_TO_MENU_TEXT
from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import AdminService

CANCEL_TEXT = BACK_TO_MENU_TEXT


def normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
    )


async def ensure_admin_or_reply(message: Message, state: FSMContext) -> bool:
    async with SessionLocal() as session:
        is_admin_user = await AdminService(session).is_admin(message.from_user.id)
    if is_admin_user:
        return True
    logger.warning("security_event non_admin_action user_id={} text={}", message.from_user.id, message.text)
    await state.clear()
    await message.answer("Эта функция доступна только администратору", reply_markup=get_main_menu(False))
    return False


async def is_admin_user(telegram_id: int) -> bool:
    async with SessionLocal() as session:
        return await AdminService(session).is_admin(telegram_id)


async def reply_main_menu(message: Message) -> None:
    await message.answer("Главное меню", reply_markup=get_main_menu(await is_admin_user(message.from_user.id)))


async def clear_and_reply_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await reply_main_menu(message)
