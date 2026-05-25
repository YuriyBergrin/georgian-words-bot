from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.db.session import SessionLocal
from app.handlers.common_helpers import CANCEL_TEXT, is_admin_user
from app.handlers.states import BrowseTopicsForm
from app.handlers.start import get_help_text
from app.keyboards.main_menu import ADMIN_PANEL_TEXT, VIEW_TOPICS_TEXT, get_admin_menu, get_main_menu
from app.keyboards.training import topics_menu
from app.services.stats_service import StatsService
from app.services.topic_service import TopicService

router = Router()
DELETE_TOPIC_TEXT = "🗑 Удалить топик"
CONFIRM_DELETE_TOPIC_YES_TEXT = "✅ Да, удалить"
CONFIRM_DELETE_TOPIC_NO_TEXT = "❌ Нет"


def browse_topics_menu(topics: list[str], admin_mode: bool) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = [[KeyboardButton(text=topic)] for topic in topics]
    if admin_mode:
        keyboard.append([KeyboardButton(text=DELETE_TOPIC_TEXT)])
    keyboard.append([KeyboardButton(text=CANCEL_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def confirm_delete_topic_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CONFIRM_DELETE_TOPIC_YES_TEXT), KeyboardButton(text=CONFIRM_DELETE_TOPIC_NO_TEXT)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == CANCEL_TEXT)
async def global_cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(await is_admin_user(message.from_user.id)))


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(await is_admin_user(message.from_user.id)))


@router.message(F.text == ADMIN_PANEL_TEXT)
async def admin_panel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not await is_admin_user(message.from_user.id):
        await message.answer("У вас нет прав администратора", reply_markup=get_main_menu(False))
        return
    await message.answer("Меню администрирования", reply_markup=get_admin_menu())


@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message) -> None:
    async with SessionLocal() as session:
        stats = await StatsService(session).get_user_stats(message.from_user.id)

    text = (
        "📊 Твоя статистика:\n\n"
        f"• Серия дней подряд: {stats['streak_days']}\n"
        f"• Всего слов в базе: {stats['total_words']}\n"
        f"• Уже тренировал(а): {stats['trained_words']}\n"
        f"• Доступно к повторению сейчас: {stats['due_words']}\n"
        f"• Правильных ответов: {stats['total_correct']}\n"
        f"• Ошибок: {stats['total_wrong']}"
    )
    await message.answer(text)


@router.message(F.text == "❓ Помощь")
async def help_button_handler(message: Message) -> None:
    await message.answer(get_help_text())


@router.message(F.text == VIEW_TOPICS_TEXT)
async def browse_topics_handler(message: Message, state: FSMContext) -> None:
    admin_mode = await is_admin_user(message.from_user.id)
    async with SessionLocal() as session:
        topics = await TopicService(session).list_topics_with_words()

    if not topics:
        await state.clear()
        await message.answer("Пока нет топиков со словами.", reply_markup=get_main_menu(admin_mode))
        return

    await state.set_state(BrowseTopicsForm.topic)
    await message.answer("Выбери топик:", reply_markup=browse_topics_menu(topics, admin_mode))


@router.message(BrowseTopicsForm.topic)
async def topic_selected_for_view_handler(message: Message, state: FSMContext) -> None:
    topic_name = message.text.strip()
    admin_mode = await is_admin_user(message.from_user.id)

    if topic_name == DELETE_TOPIC_TEXT:
        if not admin_mode:
            await state.clear()
            await message.answer("У вас нет прав администратора", reply_markup=get_main_menu(False))
            return
        async with SessionLocal() as session:
            topics = await TopicService(session).list_topics_with_words()
        await state.set_state(BrowseTopicsForm.delete_topic)
        await message.answer("Выбери топик для удаления:", reply_markup=topics_menu(topics))
        return

    async with SessionLocal() as session:
        topic_service = TopicService(session)
        topic_exists = await topic_service.topic_exists_with_words(topic_name)
        topics = await topic_service.list_topics_with_words()

        if not topic_exists:
            await message.answer("Выбери топик из списка.", reply_markup=browse_topics_menu(topics, admin_mode))
            return

        words = await topic_service.get_topic_words(topic_name)

    words_lines = [f"{index}. {georgian} — {russian}" for index, (georgian, russian) in enumerate(words, start=1)]
    text = f"🗂 Топик: {topic_name}\n\n" + "\n".join(words_lines)
    await message.answer(text, reply_markup=browse_topics_menu(topics, admin_mode))


@router.message(BrowseTopicsForm.delete_topic)
async def delete_topic_from_menu_handler(message: Message, state: FSMContext) -> None:
    if not await is_admin_user(message.from_user.id):
        await state.clear()
        await message.answer("У вас нет прав администратора", reply_markup=get_main_menu(False))
        return

    topic_name = message.text.strip()
    async with SessionLocal() as session:
        topic_service = TopicService(session)
        topic_exists = await topic_service.topic_exists_with_words(topic_name)
        topics = await topic_service.list_topics_with_words()
        if not topic_exists:
            await message.answer("Выбери топик из списка.", reply_markup=topics_menu(topics))
            return

    await state.update_data(delete_topic_name=topic_name)
    await state.set_state(BrowseTopicsForm.delete_topic_confirm)
    await message.answer(
        f"Удалить топик «{topic_name}» и все слова в нём?",
        reply_markup=confirm_delete_topic_menu(),
    )


@router.message(BrowseTopicsForm.delete_topic_confirm, F.text == CONFIRM_DELETE_TOPIC_NO_TEXT)
async def cancel_topic_delete_confirmation_handler(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        topics = await TopicService(session).list_topics_with_words()
    await state.set_state(BrowseTopicsForm.topic)
    await state.update_data(delete_topic_name=None)
    await message.answer("Удаление отменено.", reply_markup=browse_topics_menu(topics, True))


@router.message(BrowseTopicsForm.delete_topic_confirm, F.text == CONFIRM_DELETE_TOPIC_YES_TEXT)
async def confirm_topic_delete_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    topic_name = (data.get("delete_topic_name") or "").strip()
    if not topic_name:
        await state.set_state(BrowseTopicsForm.topic)
        async with SessionLocal() as session:
            topics = await TopicService(session).list_topics_with_words()
        await message.answer("Не удалось определить топик. Выбери заново.", reply_markup=browse_topics_menu(topics, True))
        return

    async with SessionLocal() as session:
        topic_service = TopicService(session)
        deleted_words = await topic_service.delete_topic_with_words(topic_name)
        if deleted_words is None:
            topics = await topic_service.list_topics_with_words()
            await state.set_state(BrowseTopicsForm.topic)
            await state.update_data(delete_topic_name=None)
            await message.answer("Топик уже удалён или не найден.", reply_markup=browse_topics_menu(topics, True))
            return
        await session.commit()
        topics = await topic_service.list_topics_with_words()

    await state.set_state(BrowseTopicsForm.topic)
    await state.update_data(delete_topic_name=None)
    if not topics:
        await state.clear()
        await message.answer("Топик удалён. Больше нет топиков со словами.", reply_markup=get_main_menu(True))
        return
    await message.answer(
        f"Топик «{topic_name}» удалён. Удалено слов: {deleted_words}.",
        reply_markup=browse_topics_menu(topics, True),
    )


@router.message(BrowseTopicsForm.delete_topic_confirm)
async def invalid_topic_delete_confirmation_handler(message: Message) -> None:
    await message.answer("Подтверди удаление кнопкой.", reply_markup=confirm_delete_topic_menu())
