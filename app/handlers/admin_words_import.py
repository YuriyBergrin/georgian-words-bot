from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.handlers.admin_words_shared import IMPORT_APPLY_TEXT, IMPORT_DRY_RUN_TEXT, IMPORT_MAX_WORDS
from app.handlers.common_helpers import cancel_menu
from app.handlers.states import BulkImportForm
from app.keyboards.main_menu import get_admin_menu
from app.middlewares.services_middleware import AppServices

router = Router()


@router.message(BulkImportForm.mode, F.text == IMPORT_DRY_RUN_TEXT)
@router.message(BulkImportForm.mode, F.text == IMPORT_APPLY_TEXT)
async def import_words_mode_handler(message: Message, state: FSMContext) -> None:
    is_dry_run = message.text == IMPORT_DRY_RUN_TEXT
    await state.update_data(import_dry_run=is_dry_run)
    await state.set_state(BulkImportForm.payload)
    await message.answer("Вставь список строк для импорта:", reply_markup=cancel_menu())


@router.message(BulkImportForm.payload)
async def import_words_payload_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    is_dry_run = bool(data.get("import_dry_run", False))
    lines = [
        line.strip()
        for line in (message.text or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if len(lines) > IMPORT_MAX_WORDS:
        await message.answer(
            f"Слишком много строк: {len(lines)}. Максимум за один импорт — {IMPORT_MAX_WORDS}.",
            reply_markup=cancel_menu(),
        )
        return

    report = await services.admin_words.import_words(message.text or "", dry_run=is_dry_run)
    logger.info(
        "admin_action import_words admin_id={} dry_run={} added={} updated={} skipped={} errors_count={}",
        message.from_user.id,
        is_dry_run,
        report.added,
        report.updated,
        report.skipped,
        report.errors_count,
    )

    await state.clear()
    text = (
        f"{'Проверка (dry-run)' if is_dry_run else 'Импорт'} завершен:\n"
        f"• Добавлено: {report.added}\n"
        f"• Обновлено: {report.updated}\n"
        f"• Пропущено: {report.skipped}\n"
        f"• Ошибок: {report.errors_count}"
    )
    errors = report.errors
    if errors:
        text += "\n\n" + "\n".join(errors[:10])
    await message.answer(text, reply_markup=get_admin_menu())
