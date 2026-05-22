from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu(is_admin_user: bool) -> ReplyKeyboardMarkup:
    first_row = [KeyboardButton(text="📚 Учить слова")]
    if is_admin_user:
        first_row.append(KeyboardButton(text="➕ Добавить слово"))

    return ReplyKeyboardMarkup(
        keyboard=[
            first_row,
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )
