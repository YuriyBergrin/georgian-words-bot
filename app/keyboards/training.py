from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BACK_TO_MENU_TEXT = "🔙 Назад в меню"
TRAIN_ALL_WORDS_TEXT = "🌍 Все слова"
TRAIN_BY_TOPIC_TEXT = "📂 Выбрать тему"
REPEAT_TOPIC_TEXT = "🔁 Повторить тему"


def training_mode_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TRAIN_ALL_WORDS_TEXT), KeyboardButton(text=TRAIN_BY_TOPIC_TEXT)],
            [KeyboardButton(text=BACK_TO_MENU_TEXT)],
        ],
        resize_keyboard=True,
    )


def topics_menu(topics: list[str]) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=topic)] for topic in topics]
    keyboard.append([KeyboardButton(text=BACK_TO_MENU_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def translation_options_menu(options: list[str]) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for option in options:
        row.append(KeyboardButton(text=option))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(text=BACK_TO_MENU_TEXT)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def topic_completed_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=REPEAT_TOPIC_TEXT)],
            [KeyboardButton(text=BACK_TO_MENU_TEXT)],
        ],
        resize_keyboard=True,
    )
