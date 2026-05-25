from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

ADMIN_PANEL_TEXT = "🛠 Админ-меню"
BACK_TO_MAIN_MENU_TEXT = "🔙 Назад в меню"
VIEW_TOPICS_TEXT = "🗂 Топики слов"


def get_main_menu(is_admin_user: bool) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = [
        [KeyboardButton(text="📚 Учить слова"), KeyboardButton(text=VIEW_TOPICS_TEXT)],
        [KeyboardButton(text=ADMIN_PANEL_TEXT)],
    ]
    if is_admin_user:
        keyboard.append([KeyboardButton(text="📊 Статистика")])
        keyboard.append([KeyboardButton(text="❓ Помощь")])
    else:
        keyboard.append([KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Помощь")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_admin_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="➕ Добавить слово")],
        [KeyboardButton(text="📥 Импорт слов"), KeyboardButton(text="📤 Экспорт слов")],
        [KeyboardButton(text="🔎 Найти слово"), KeyboardButton(text="🔥 Топ сложных слов")],
        [KeyboardButton(text=BACK_TO_MAIN_MENU_TEXT)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
