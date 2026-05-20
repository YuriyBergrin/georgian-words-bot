from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Учить слова"), KeyboardButton(text="➕ Добавить слово")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True,
)
