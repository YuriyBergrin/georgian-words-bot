from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from loguru import logger

from app.db.session import SessionLocal
from app.handlers.admin_words_add import router as add_router
from app.handlers.admin_words_edit import router as edit_router
from app.handlers.admin_words_import import router as import_router
from app.handlers.admin_words_search import router as search_router
from app.handlers.admin_words_shared import IMPORT_MAX_WORDS, import_mode_menu
from app.handlers.common_helpers import CANCEL_TEXT, cancel_menu, ensure_admin_or_reply
from app.handlers.states import AddWordForm, BulkImportForm, DeleteWordForm, EditWordForm, SearchWordForm
from app.keyboards.main_menu import get_admin_menu
from app.services.word_query_service import WordQueryService

router = Router()
router.include_router(import_router)
router.include_router(search_router)
router.include_router(edit_router)
router.include_router(add_router)


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
    await state.set_state(BulkImportForm.mode)
    await message.answer(
        f"Формат: georgian | russian | topic\nПример: მივდივარ | я иду | движение\nЛимит за один импорт: {IMPORT_MAX_WORDS} строк.",
        reply_markup=import_mode_menu(),
    )


@router.message(F.text == "📤 Экспорт слов")
async def export_words_handler(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_or_reply(message, state):
        return
    async with SessionLocal() as session:
        rows = await WordQueryService(session).export_words_rows()

    lines = [f"{georgian} | {russian} | {topic}" for georgian, russian, topic in rows]
    payload = "\n".join(lines) if lines else ""
    file = BufferedInputFile(payload.encode("utf-8"), filename="words_export.txt")
    await message.answer_document(file, caption=f"Экспорт слов: {len(rows)}")
    logger.info("admin_action export_words admin_id={} count={}", message.from_user.id, len(rows))


@router.message(F.text == "✏️ Редактировать слово")
async def edit_word_handler(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_or_reply(message, state):
        return
    await state.set_state(EditWordForm.georgian)
    await message.answer("Введи грузинское слово для редактирования:", reply_markup=cancel_menu())


@router.message(F.text == "🔎 Найти слово")
async def search_words_handler(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_or_reply(message, state):
        return
    await state.set_state(SearchWordForm.query)
    await message.answer("Введи текст для поиска (грузинское, русский перевод или тема):", reply_markup=cancel_menu())


@router.message(BulkImportForm.payload, F.text == CANCEL_TEXT)
@router.message(BulkImportForm.mode, F.text == CANCEL_TEXT)
@router.message(EditWordForm.georgian, F.text == CANCEL_TEXT)
@router.message(EditWordForm.russian, F.text == CANCEL_TEXT)
@router.message(EditWordForm.topic, F.text == CANCEL_TEXT)
@router.message(SearchWordForm.query, F.text == CANCEL_TEXT)
@router.message(SearchWordForm.browse, F.text == CANCEL_TEXT)
@router.message(DeleteWordForm.georgian, F.text == CANCEL_TEXT)
@router.message(AddWordForm.georgian, F.text == CANCEL_TEXT)
@router.message(AddWordForm.russian, F.text == CANCEL_TEXT)
@router.message(AddWordForm.topic, F.text == CANCEL_TEXT)
@router.message(AddWordForm.topic_custom, F.text == CANCEL_TEXT)
async def cancel_admin_forms_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Меню администрирования", reply_markup=get_admin_menu())
