from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.keyboards.training import BACK_TO_MENU_TEXT
from app.keyboards.main_menu import get_main_menu, get_admin_menu

CANCEL_TEXT = BACK_TO_MENU_TEXT


def normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
    )


async def reply_main_menu(message: Message, is_admin: bool) -> None:
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin))


async def clear_and_reply_main_menu(message: Message, state: FSMContext, is_admin: bool) -> None:
    await state.clear()
    await reply_main_menu(message, is_admin)


async def reply_admin_menu(message: Message) -> None:
    await message.answer("Меню администрирования", reply_markup=get_admin_menu())
