from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.handlers.admin_words_edit import start_edit_word_flow
from app.handlers.admin_words_shared import (
    DELETE_WORD_TEXT,
    EDIT_WORD_TEXT,
    SEARCH_NEXT_TEXT,
    SEARCH_PAGE_SIZE,
    SEARCH_PREV_TEXT,
    search_browse_menu,
)
from app.handlers.common_helpers import cancel_menu
from app.handlers.states import DeleteWordForm, SearchWordForm
from app.middlewares.services_middleware import AppServices

router = Router()


async def _render_search_page(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    query = data.get("search_query", "")
    page = int(data.get("search_page", 0))

    search_page = await services.admin_words.search_words(query=query, page=page, page_size=SEARCH_PAGE_SIZE)
    total = search_page.total
    rows = search_page.rows

    if total == 0:
        await state.set_state(SearchWordForm.query)
        await message.answer("Ничего не найдено. Введи другой запрос:", reply_markup=cancel_menu())
        return

    page_count = (total + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE
    lines = [f"Результаты поиска: {query}", f"Страница {page + 1}/{page_count}"]
    for idx, (georgian, russian, topic) in enumerate(rows, start=1 + page * SEARCH_PAGE_SIZE):
        topic_text = topic if topic else "-"
        lines.append(f"{idx}. {georgian} — {russian} [{topic_text}]")

    has_prev = page > 0
    has_next = (page + 1) * SEARCH_PAGE_SIZE < total
    await state.update_data(
        search_rows=[georgian for georgian, _, _ in rows],
        search_row_start=1 + page * SEARCH_PAGE_SIZE,
    )
    await state.set_state(SearchWordForm.browse)
    await message.answer("\n".join(lines), reply_markup=search_browse_menu(has_prev, has_next))


@router.message(SearchWordForm.query)
async def search_words_query_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Запрос пустой. Введи текст для поиска:", reply_markup=cancel_menu())
        return
    await state.update_data(search_query=query, search_page=0)
    await _render_search_page(message, state, services)


@router.message(SearchWordForm.browse, F.text == SEARCH_PREV_TEXT)
async def search_words_prev_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    page = max(int(data.get("search_page", 0)) - 1, 0)
    await state.update_data(search_page=page)
    await _render_search_page(message, state, services)


@router.message(SearchWordForm.browse, F.text == SEARCH_NEXT_TEXT)
async def search_words_next_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    page = int(data.get("search_page", 0)) + 1
    await state.update_data(search_page=page)
    await _render_search_page(message, state, services)


@router.message(SearchWordForm.browse, F.text == EDIT_WORD_TEXT)
async def edit_word_from_search_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    search_rows = data.get("search_rows", [])
    if len(search_rows) == 1:
        await start_edit_word_flow(message, state, search_rows[0], services)
        return
    if search_rows:
        await message.answer(
            "Найдено несколько слов. Отправь номер из списка или грузинское слово для редактирования.",
            reply_markup=cancel_menu(),
        )
        return
    await message.answer("Список поиска пуст. Выполни поиск заново.", reply_markup=cancel_menu())


@router.message(SearchWordForm.browse, F.text == DELETE_WORD_TEXT)
async def delete_word_start_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(DeleteWordForm.georgian)
    await message.answer("Введи грузинское слово для удаления:", reply_markup=cancel_menu())


@router.message(SearchWordForm.browse)
async def pick_word_from_search_handler(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    search_rows = data.get("search_rows", [])
    row_start = int(data.get("search_row_start", 1))
    if not search_rows:
        await message.answer("Список поиска пуст. Выполни поиск заново.", reply_markup=cancel_menu())
        return

    if text.isdigit():
        idx = int(text)
        offset = idx - row_start
        if 0 <= offset < len(search_rows):
            await start_edit_word_flow(message, state, search_rows[offset], services)
            return
        await message.answer("Номер вне текущей страницы. Выбери номер из списка.", reply_markup=cancel_menu())
        return

    if text in search_rows:
        await start_edit_word_flow(message, state, text, services)
        return

    await message.answer(
        "Для редактирования нажми кнопку или отправь номер из списка/грузинское слово.",
        reply_markup=cancel_menu(),
    )
