from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import SessionLocal
from app.handlers.common_helpers import CANCEL_TEXT, cancel_menu, ensure_admin_or_reply
from app.handlers.states import AddWordForm, BulkImportForm, EditWordForm
from app.keyboards.main_menu import get_main_menu
from app.services.admin_service import is_admin
from app.services.word_service import WordService

router = Router()


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
        "Вставь список строк в формате:\ngeorgian | russian | topic\n\nПример:\nმივდივარ | я иду | движение",
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
async def cancel_admin_forms_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(BulkImportForm.payload)
async def import_words_payload_handler(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        report = await WordService(session).bulk_import_from_text(message.text or "")

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
    await state.update_data(georgian=message.text.strip())
    await state.set_state(EditWordForm.russian)
    await message.answer("Введи новый русский перевод:", reply_markup=cancel_menu())


@router.message(EditWordForm.russian)
async def edit_word_russian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(russian=message.text.strip())
    await state.set_state(EditWordForm.topic)
    await message.answer("Введи новую тему (или '-' чтобы убрать):", reply_markup=cancel_menu())


@router.message(EditWordForm.topic)
async def edit_word_topic_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    georgian = data["georgian"]
    russian = data["russian"]
    topic_name = message.text.strip()
    async with SessionLocal() as session:
        updated = await WordService(session).update_word(
            georgian=georgian,
            new_russian=russian,
            new_topic_name=topic_name,
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
    await message.answer("Введите тему слова (или '-' чтобы пропустить):", reply_markup=cancel_menu())


@router.message(AddWordForm.topic)
async def add_word_topic_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    georgian = data["georgian"]
    russian = data["russian"]
    topic_name = message.text.strip()

    async with SessionLocal() as session:
        created = await WordService(session).add_word(
            georgian=georgian,
            russian=russian,
            topic_name=topic_name,
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

