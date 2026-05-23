from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from loguru import logger

from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import is_admin

CANCEL_TEXT = "❌ Отмена"


def normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
    )


async def ensure_admin_or_reply(message: Message, state: FSMContext) -> bool:
    if is_admin(message.from_user.id):
        return True
    logger.warning("security_event non_admin_action user_id={} text={}", message.from_user.id, message.text)
    await state.clear()
    await message.answer("Эта функция доступна только администратору", reply_markup=get_main_menu(False))
    return False
