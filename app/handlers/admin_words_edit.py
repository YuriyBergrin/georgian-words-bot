from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.db.session import SessionLocal
from app.handlers.admin_words_shared import KEEP_TOPIC_TEXT, REMOVE_TOPIC_TEXT, edit_topic_menu
from app.handlers.common_helpers import cancel_menu
from app.handlers.states import DeleteWordForm, EditWordForm
from app.keyboards.main_menu import get_admin_menu
from app.services.topic_service import TopicService
from app.services.word_service import WordService

router = Router()


async def start_edit_word_flow(message: Message, state: FSMContext, georgian: str) -> None:
    georgian = georgian.strip()
    async with SessionLocal() as session:
        word_service = WordService(session)
        exists = await word_service.word_exists(georgian)
        if not exists:
            await message.answer("Слово не найдено. Введи другое слово или нажми отмену.", reply_markup=cancel_menu())
            return
        current_topic = await word_service.get_word_topic_name(georgian)

    await state.update_data(georgian=georgian, current_topic=current_topic)
    await state.set_state(EditWordForm.georgian_new)
    await message.answer(
        f"Текущее грузинское слово: {georgian}\nВведи новое грузинское слово (или отправь текущее без изменений):",
        reply_markup=cancel_menu(),
    )


@router.message(DeleteWordForm.georgian)
async def delete_word_handler(message: Message, state: FSMContext) -> None:
    georgian = message.text.strip()
    async with SessionLocal() as session:
        deleted = await WordService(session).delete_word(georgian)
    logger.info("admin_action delete_word admin_id={} georgian={} deleted={}", message.from_user.id, georgian, deleted)
    await state.clear()
    if deleted:
        await message.answer("Слово удалено.", reply_markup=get_admin_menu())
    else:
        await message.answer("Слово не найдено.", reply_markup=get_admin_menu())


@router.message(EditWordForm.georgian)
async def edit_word_georgian_handler(message: Message, state: FSMContext) -> None:
    await start_edit_word_flow(message, state, message.text or "")


@router.message(EditWordForm.georgian_new)
async def edit_word_georgian_new_handler(message: Message, state: FSMContext) -> None:
    new_georgian = message.text.strip()
    if not new_georgian:
        await message.answer("Грузинское слово не может быть пустым. Введи значение:", reply_markup=cancel_menu())
        return
    await state.update_data(georgian_new=new_georgian)
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
    georgian_new = data["georgian_new"]
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
        update_status = await WordService(session).update_word(
            georgian=georgian,
            new_georgian=georgian_new,
            new_russian=russian,
            new_topic_name=topic_name,
        )
    logger.info(
        "admin_action edit_word admin_id={} georgian={} georgian_new={} status={} topic={}",
        message.from_user.id,
        georgian,
        georgian_new,
        update_status,
        topic_name,
    )

    await state.clear()
    if update_status == "updated":
        await message.answer("Слово обновлено.", reply_markup=get_admin_menu())
    elif update_status == "duplicate":
        await message.answer("Такое грузинское слово уже есть в словаре.", reply_markup=get_admin_menu())
    else:
        await message.answer("Слово не найдено.", reply_markup=get_admin_menu())
