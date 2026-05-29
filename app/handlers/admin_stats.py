from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.keyboards.main_menu import get_admin_menu, get_main_menu
from app.middlewares.services_middleware import AppServices

router = Router()


@router.message(F.text == "🔥 Топ сложных слов")
async def hard_words_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    if not await services.access.is_admin_user(message.from_user.id):
        await state.clear()
        await message.answer("Эта функция доступна только администратору", reply_markup=get_main_menu(False))
        return
    hard_words = await services.admin_stats.get_hard_words(limit=10)
    logger.info("admin_action hard_words admin_id={} result_count={}", message.from_user.id, len(hard_words))
    if not hard_words:
        await message.answer("Пока нет данных по сложным словам.", reply_markup=get_admin_menu())
        return
    lines = ["🔥 Топ сложных слов:"]
    for idx, (georgian, russian, wrong, correct) in enumerate(hard_words, start=1):
        lines.append(f"{idx}. {georgian} — {russian} (ошибок: {wrong}, верных: {correct})")
    await message.answer("\n".join(lines), reply_markup=get_admin_menu())
