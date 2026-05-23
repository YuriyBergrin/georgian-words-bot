from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu(is_admin_user: bool) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = [[KeyboardButton(text="📚 Учить слова")]]
    if is_admin_user:
        keyboard[0].append(KeyboardButton(text="➕ Добавить слово"))
        keyboard.append([KeyboardButton(text="📥 Импорт слов"), KeyboardButton(text="✏️ Редактировать слово")])
        keyboard.append([KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🔥 Топ сложных слов")])
        keyboard.append([KeyboardButton(text="❓ Помощь")])
    else:
        keyboard.append([KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Помощь")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
