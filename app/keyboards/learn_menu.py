from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

learn_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➡️ Следующее слово")],
        [KeyboardButton(text="🏠 Главное меню")],
    ],
    resize_keyboard=True,
)
