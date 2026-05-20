from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.keyboards.learn_menu import learn_menu
from app.keyboards.main_menu import main_menu
from app.models.topic import Topic
from app.models.word import Word

router = Router()


class AddWordForm(StatesGroup):
    georgian = State()
    russian = State()
    topic = State()


class LearnWordForm(StatesGroup):
    answer = State()


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


async def _send_random_word(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(Word).order_by(func.random()).limit(1))
        word = result.scalar_one_or_none()

    if word is None:
        await state.clear()
        await message.answer("Слов пока нет. Добавь слово через меню.", reply_markup=main_menu)
        return

    await state.set_state(LearnWordForm.answer)
    await state.update_data(word_id=word.id)
    await message.answer(f"Переведи слово: {word.georgian}")


@router.message(F.text == "📚 Учить слова")
async def learn_words_handler(message: Message, state: FSMContext) -> None:
    await _send_random_word(message, state)


@router.message(F.text == "➕ Добавить слово")
async def add_word_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWordForm.georgian)
    await message.answer("Введите грузинское слово:")


@router.message(AddWordForm.georgian)
async def add_word_georgian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(georgian=message.text.strip())
    await state.set_state(AddWordForm.russian)
    await message.answer("Введите русский перевод:")


@router.message(AddWordForm.russian)
async def add_word_russian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(russian=message.text.strip())
    await state.set_state(AddWordForm.topic)
    await message.answer("Введите тему слова (или '-' чтобы пропустить):")


@router.message(AddWordForm.topic)
async def add_word_topic_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    georgian = data["georgian"]
    russian = data["russian"]
    topic_name = message.text.strip()

    async with SessionLocal() as session:
        existing_result = await session.execute(select(Word).where(Word.georgian == georgian))
        existing_word = existing_result.scalar_one_or_none()
        if existing_word is not None:
            await state.clear()
            await message.answer("Такое слово уже есть в словаре", reply_markup=main_menu)
            return

        topic = None
        if topic_name != "-":
            topic_result = await session.execute(select(Topic).where(Topic.name == topic_name))
            topic = topic_result.scalar_one_or_none()
            if topic is None:
                topic = Topic(name=topic_name)
                session.add(topic)
                await session.flush()

        word = Word(georgian=georgian, russian=russian, topic_id=topic.id if topic else None)
        session.add(word)
        await session.commit()

    await state.clear()
    await message.answer("Слово добавлено", reply_markup=main_menu)


@router.message(LearnWordForm.answer)
async def learn_word_answer_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    word_id = data["word_id"]

    async with SessionLocal() as session:
        result = await session.execute(select(Word).where(Word.id == word_id))
        word = result.scalar_one_or_none()

    if word is None:
        await state.clear()
        await message.answer("Слово не найдено. Попробуй снова.", reply_markup=main_menu)
        return

    user_answer = _normalize_text(message.text)
    correct_answer = _normalize_text(word.russian)
    await state.clear()

    if user_answer == correct_answer:
        await message.answer("✅ Верно", reply_markup=learn_menu)
    else:
        await message.answer(f"❌ Неверно. Правильный ответ: {word.russian}", reply_markup=learn_menu)


@router.message(F.text == "➡️ Следующее слово")
async def next_word_handler(message: Message, state: FSMContext) -> None:
    await _send_random_word(message, state)


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu)


@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message) -> None:
    await message.answer("Статистика пока в разработке.")


@router.message(F.text == "⚙️ Настройки")
async def settings_handler(message: Message) -> None:
    await message.answer("Настройки пока в разработке.")
