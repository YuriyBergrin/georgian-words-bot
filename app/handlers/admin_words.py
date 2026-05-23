from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from loguru import logger

from app.db.session import SessionLocal
from app.handlers.common_helpers import CANCEL_TEXT, cancel_menu, ensure_admin_or_reply
from app.handlers.states import AddWordForm, BulkImportForm, EditWordForm
from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import is_admin
from app.services.topic_service import TopicService
from app.services.word_service import WordService

router = Router()
KEEP_TOPIC_TEXT = "✅ Оставить текущую тему"
REMOVE_TOPIC_TEXT = "➖ Убрать тему"
NEW_TOPIC_TEXT = "✍️ Ввести новую тему"
SKIP_TOPIC_TEXT = "⏭️ Без темы"


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


@router.message(F.text == "➕ Добавить слово")
async def add_word_handler(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_or_reply(message, state):
        return
    await state.set_state(AddWordForm.georgian)
    await message.answer("Введите грузинское слово:", reply_markup=cancel_menu())


@router.message(F.text == "📥 Импорт слов")
async def import_words_handler(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_or_reply(message, state):
        return
    await state.set_state(BulkImportForm.payload)
    await message.answer(
        "Вставь список строк в формате:\ngeorgian | russian | topic\n\nПример:\nმივდივარ | я иду | движение\nმიდიხარ | ты идёшь | движение",
        reply_markup=cancel_menu(),
    )


@router.message(F.text == "✏️ Редактировать слово")
async def edit_word_handler(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_or_reply(message, state):
        return
    await state.set_state(EditWordForm.georgian)
    await message.answer("Введи грузинское слово для редактирования:", reply_markup=cancel_menu())


@router.message(BulkImportForm.payload, F.text == CANCEL_TEXT)
@router.message(EditWordForm.georgian, F.text == CANCEL_TEXT)
@router.message(EditWordForm.russian, F.text == CANCEL_TEXT)
@router.message(EditWordForm.topic, F.text == CANCEL_TEXT)
@router.message(AddWordForm.georgian, F.text == CANCEL_TEXT)
@router.message(AddWordForm.russian, F.text == CANCEL_TEXT)
@router.message(AddWordForm.topic, F.text == CANCEL_TEXT)
@router.message(AddWordForm.topic_custom, F.text == CANCEL_TEXT)
async def cancel_admin_forms_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(BulkImportForm.payload)
async def import_words_payload_handler(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        report = await WordService(session).bulk_import_from_text(message.text or "")
    logger.info(
        "admin_action import_words admin_id={} added={} updated={} skipped={} errors_count={}",
        message.from_user.id,
        report["added"],
        report["updated"],
        report["skipped"],
        report["errors_count"],
    )

    await state.clear()
    text = (
        "Импорт завершен:\n"
        f"• Добавлено: {report['added']}\n"
        f"• Обновлено: {report['updated']}\n"
        f"• Пропущено: {report['skipped']}\n"
        f"• Ошибок: {report['errors_count']}"
    )
    errors = report.get("errors", [])
    if errors:
        text += "\n\n" + "\n".join(errors[:10])
    await message.answer(text, reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(EditWordForm.georgian)
async def edit_word_georgian_handler(message: Message, state: FSMContext) -> None:
    georgian = message.text.strip()
    async with SessionLocal() as session:
        word_service = WordService(session)
        exists = await word_service.word_exists(georgian)
        if not exists:
            await message.answer("Слово не найдено. Введи другое слово или нажми отмену.", reply_markup=cancel_menu())
            return
        current_topic = await word_service.get_word_topic_name(georgian)

    await state.update_data(georgian=georgian, current_topic=current_topic)
    await state.set_state(EditWordForm.russian)
    await message.answer("Введи новый русский перевод:", reply_markup=cancel_menu())


@router.message(EditWordForm.russian)
async def edit_word_russian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(russian=message.text.strip())
    await state.set_state(EditWordForm.topic)
    data = await state.get_data()
    current_topic = data.get("current_topic")
    async with SessionLocal() as session:
        topics = await TopicService(session).list_topics_with_words()
    await state.update_data(edit_topics=topics)
    current_topic_text = current_topic if current_topic is not None else "без темы"
    await message.answer(
        f"Текущая тема: {current_topic_text}\nВыбери новую тему кнопкой:",
        reply_markup=edit_topic_menu(topics, current_topic),
    )


@router.message(EditWordForm.topic)
async def edit_word_topic_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    georgian = data["georgian"]
    russian = data["russian"]
    current_topic = data.get("current_topic")
    topics = data.get("edit_topics", [])
    topic_input = message.text.strip()

    if topic_input == KEEP_TOPIC_TEXT:
        topic_name = current_topic if current_topic is not None else "-"
    elif topic_input == REMOVE_TOPIC_TEXT:
        topic_name = "-"
    elif topic_input in topics:
        topic_name = topic_input
    else:
        await message.answer("Выбери тему кнопкой.", reply_markup=edit_topic_menu(topics, current_topic))
        return

    async with SessionLocal() as session:
        updated = await WordService(session).update_word(
            georgian=georgian,
            new_russian=russian,
            new_topic_name=topic_name,
        )
    logger.info(
        "admin_action edit_word admin_id={} georgian={} updated={} topic={}",
        message.from_user.id,
        georgian,
        updated,
        topic_name,
    )

    await state.clear()
    if updated:
        await message.answer("Слово обновлено.", reply_markup=get_main_menu(is_admin(message.from_user.id)))
    else:
        await message.answer("Слово не найдено.", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(AddWordForm.georgian)
async def add_word_georgian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(georgian=message.text.strip())
    await state.set_state(AddWordForm.russian)
    await message.answer("Введите русский перевод:", reply_markup=cancel_menu())


@router.message(AddWordForm.russian)
async def add_word_russian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(russian=message.text.strip())
    await state.set_state(AddWordForm.topic)
    async with SessionLocal() as session:
        topics = await TopicService(session).list_topics_with_words()
    await state.update_data(add_topics=topics)
    await message.answer(
        "Выбери тему из списка или введи новую:",
        reply_markup=add_topic_menu(topics),
    )


@router.message(AddWordForm.topic)
async def add_word_topic_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    georgian = data["georgian"]
    russian = data["russian"]
    topics = data.get("add_topics", [])
    topic_input = message.text.strip()

    if topic_input == NEW_TOPIC_TEXT:
        await state.set_state(AddWordForm.topic_custom)
        await message.answer("Введи новую тему:", reply_markup=cancel_menu())
        return
    if topic_input == SKIP_TOPIC_TEXT:
        topic_name = "-"
    elif topic_input in topics:
        topic_name = topic_input
    else:
        await message.answer("Выбери тему кнопкой или выбери ввод новой темы.", reply_markup=add_topic_menu(topics))
        return

    async with SessionLocal() as session:
        created = await WordService(session).add_word(
            georgian=georgian,
            russian=russian,
            topic_name=topic_name,
        )
        logger.info(
            "admin_action add_word admin_id={} georgian={} created={} topic={}",
            message.from_user.id,
            georgian,
            created,
            topic_name,
        )
        if not created:
            await state.clear()
            await message.answer(
                "Такое слово уже есть в словаре",
                reply_markup=get_main_menu(is_admin(message.from_user.id)),
            )
            return

    await state.clear()
    await message.answer("Слово добавлено", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(AddWordForm.topic_custom)
async def add_word_topic_custom_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    georgian = data["georgian"]
    russian = data["russian"]
    topic_name = message.text.strip()
    if not topic_name:
        await message.answer("Тема не может быть пустой. Введи тему:", reply_markup=cancel_menu())
        return

    async with SessionLocal() as session:
        created = await WordService(session).add_word(
            georgian=georgian,
            russian=russian,
            topic_name=topic_name,
        )
        logger.info(
            "admin_action add_word_custom_topic admin_id={} georgian={} created={} topic={}",
            message.from_user.id,
            georgian,
            created,
            topic_name,
        )
        if not created:
            await state.clear()
            await message.answer(
                "Такое слово уже есть в словаре",
                reply_markup=get_main_menu(is_admin(message.from_user.id)),
            )
            return

    await state.clear()
    await message.answer("Слово добавлено", reply_markup=get_main_menu(is_admin(message.from_user.id)))
