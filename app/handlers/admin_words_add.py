from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.db.session import SessionLocal
from app.handlers.common_helpers import cancel_menu
from app.handlers.states import AddWordForm
from app.keyboards.main_menu import get_admin_menu
from app.services.topic_service import TopicService
from app.services.word_service import WordService
from app.handlers.admin_words_shared import NEW_TOPIC_TEXT, SKIP_TOPIC_TEXT, add_topic_menu

router = Router()


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
                reply_markup=get_admin_menu(),
            )
            return

    await state.clear()
    await message.answer("Слово добавлено", reply_markup=get_admin_menu())


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
                reply_markup=get_admin_menu(),
            )
            return

    await state.clear()
    await message.answer("Слово добавлено", reply_markup=get_admin_menu())
