from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.handlers.common_helpers import CANCEL_TEXT

KEEP_TOPIC_TEXT = "✅ Оставить текущую тему"
REMOVE_TOPIC_TEXT = "➖ Убрать тему"
NEW_TOPIC_TEXT = "✍️ Ввести новую тему"
SKIP_TOPIC_TEXT = "⏭️ Без темы"
IMPORT_DRY_RUN_TEXT = "🧪 Проверка (dry-run)"
IMPORT_APPLY_TEXT = "💾 Импортировать"
SEARCH_PREV_TEXT = "⬅️ Назад"
SEARCH_NEXT_TEXT = "➡️ Вперед"
DELETE_WORD_TEXT = "🗑 Удалить слово"
SEARCH_PAGE_SIZE = 10
IMPORT_MAX_WORDS = 50


def edit_topic_menu(topics: list[str], current_topic: str | None) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = [[KeyboardButton(text=KEEP_TOPIC_TEXT)]]
    if current_topic is not None:
        keyboard[0].append(KeyboardButton(text=REMOVE_TOPIC_TEXT))
    for topic in topics:
        if topic != current_topic:
            keyboard.append([KeyboardButton(text=topic)])
    keyboard.append([KeyboardButton(text=CANCEL_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def add_topic_menu(topics: list[str]) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = [[KeyboardButton(text=NEW_TOPIC_TEXT), KeyboardButton(text=SKIP_TOPIC_TEXT)]]
    for topic in topics:
        keyboard.append([KeyboardButton(text=topic)])
    keyboard.append([KeyboardButton(text=CANCEL_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def import_mode_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=IMPORT_DRY_RUN_TEXT), KeyboardButton(text=IMPORT_APPLY_TEXT)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
    )


def search_browse_menu(has_prev: bool, has_next: bool) -> ReplyKeyboardMarkup:
    row: list[KeyboardButton] = []
    if has_prev:
        row.append(KeyboardButton(text=SEARCH_PREV_TEXT))
    if has_next:
        row.append(KeyboardButton(text=SEARCH_NEXT_TEXT))
    keyboard: list[list[KeyboardButton]] = [row] if row else []
    keyboard.append([KeyboardButton(text="✏️ Редактировать слово"), KeyboardButton(text=DELETE_WORD_TEXT)])
    keyboard.append([KeyboardButton(text=CANCEL_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
