from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import SessionLocal
from app.handlers.common_helpers import CANCEL_TEXT
from app.handlers.start import get_help_text
from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import is_admin
from app.services.stats_service import StatsService

router = Router()


@router.message(F.text == CANCEL_TEXT)
async def global_cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message) -> None:
    async with SessionLocal() as session:
        stats = await StatsService(session).get_user_stats(message.from_user.id)

    text = (
        "📊 Твоя статистика:\n\n"
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
