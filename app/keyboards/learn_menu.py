from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from app.keyboards.training import BACK_TO_MENU_TEXT

learn_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BACK_TO_MENU_TEXT)],
    ],
    resize_keyboard=True,
)
