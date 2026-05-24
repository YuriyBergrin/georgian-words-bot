from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import SessionLocal
from app.handlers.common_helpers import CANCEL_TEXT, is_admin_user
from app.handlers.start import get_help_text
from app.keyboards.main_menu import get_main_menu
from app.services.stats_service import StatsService

router = Router()


@router.message(F.text == CANCEL_TEXT)
async def global_cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(await is_admin_user(message.from_user.id)))


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(await is_admin_user(message.from_user.id)))


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
