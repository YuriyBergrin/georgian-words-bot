from datetime import datetime, timezone
from datetime import timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy import and_, func, or_, select

from app.db.session import SessionLocal
from app.keyboards.learn_menu import learn_menu
from app.keyboards.main_menu import get_main_menu
from app.models.topic import Topic
from app.models.user import User
from app.models.user_word_progress import UserWordProgress
from app.models.word import Word
from app.services.admin_service import is_admin

router = Router()
CANCEL_ADD_WORD_TEXT = "❌ Отмена"
BACK_TO_MENU_TEXT = "🔙 Назад в меню"
TRAIN_ALL_WORDS_TEXT = "🌍 Все слова"
TRAIN_BY_TOPIC_TEXT = "📂 Выбрать тему"


class AddWordForm(StatesGroup):
    georgian = State()
    russian = State()
    topic = State()


class LearnWordForm(StatesGroup):
    mode = State()
    topic = State()
    answer = State()


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


def _add_word_cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_ADD_WORD_TEXT)]],
        resize_keyboard=True,
    )


def _training_mode_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TRAIN_ALL_WORDS_TEXT), KeyboardButton(text=TRAIN_BY_TOPIC_TEXT)],
            [KeyboardButton(text=BACK_TO_MENU_TEXT)],
        ],
        resize_keyboard=True,
    )


def _topics_menu(topics: list[str]) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=topic)] for topic in topics]
    keyboard.append([KeyboardButton(text=BACK_TO_MENU_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def get_random_word(session, user_id: int, topic: str | None = None) -> Word | None:
    now = datetime.now(timezone.utc)
    query = (
        select(Word)
        .outerjoin(
            UserWordProgress,
            and_(
                UserWordProgress.word_id == Word.id,
                UserWordProgress.user_id == user_id,
            ),
        )
        .where(
            or_(
                UserWordProgress.next_review_at.is_(None),
                UserWordProgress.next_review_at <= now,
            )
        )
    )

    if topic is not None:
        query = query.join(Topic, Word.topic_id == Topic.id).where(Topic.name == topic)

    result = await session.execute(query.order_by(func.random()).limit(1))
    return result.scalar_one_or_none()


async def _send_random_word(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    selected_topic = data.get("selected_topic")

    async with SessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )
            session.add(user)
            await session.flush()
            await session.commit()

        word = await get_random_word(session, user_id=user.id, topic=selected_topic)

    if word is None:
        if selected_topic is None:
            await message.answer("Пока нет слов для повторения.", reply_markup=learn_menu)
        else:
            await message.answer("В этой теме пока нет слов", reply_markup=learn_menu)
        return

    await state.set_state(LearnWordForm.answer)
    await state.update_data(word_id=word.id)
    await message.answer(f"Переведи слово: {word.georgian}")


@router.message(F.text == "📚 Учить слова")
async def learn_words_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(LearnWordForm.mode)
    await message.answer("Выбери режим тренировки:", reply_markup=_training_mode_menu())


@router.message(LearnWordForm.mode, F.text == TRAIN_ALL_WORDS_TEXT)
async def learn_all_words_mode_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(selected_topic=None)
    await _send_random_word(message, state)


@router.message(LearnWordForm.mode, F.text == TRAIN_BY_TOPIC_TEXT)
async def learn_by_topic_mode_handler(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        topics_result = await session.execute(select(Topic.name).join(Word, Word.topic_id == Topic.id).distinct().order_by(Topic.name))
        topics = list(topics_result.scalars().all())

    if not topics:
        await state.set_state(LearnWordForm.mode)
        await message.answer("Темы пока не добавлены", reply_markup=_training_mode_menu())
        return

    await state.set_state(LearnWordForm.topic)
    await message.answer("Выбери тему:", reply_markup=_topics_menu(topics))


@router.message(LearnWordForm.topic)
async def learn_topic_selected_handler(message: Message, state: FSMContext) -> None:
    topic_name = message.text.strip()
    if topic_name == BACK_TO_MENU_TEXT:
        await state.clear()
        await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))
        return

    async with SessionLocal() as session:
        exists_result = await session.execute(
            select(Topic.id).join(Word, Word.topic_id == Topic.id).where(Topic.name == topic_name).limit(1)
        )
        topic_exists = exists_result.scalar_one_or_none() is not None
        topics_result = await session.execute(select(Topic.name).join(Word, Word.topic_id == Topic.id).distinct().order_by(Topic.name))
        topics = list(topics_result.scalars().all())

    if not topic_exists:
        await message.answer("Выбери тему из списка.", reply_markup=_topics_menu(topics))
        return

    await state.update_data(selected_topic=topic_name)
    await _send_random_word(message, state)


@router.message(LearnWordForm.mode, F.text == BACK_TO_MENU_TEXT)
@router.message(LearnWordForm.topic, F.text == BACK_TO_MENU_TEXT)
async def back_from_training_mode_to_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(F.text == "➕ Добавить слово")
async def add_word_handler(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(
            "Эта функция доступна только администратору",
            reply_markup=get_main_menu(False),
        )
        return

    await state.set_state(AddWordForm.georgian)
    await message.answer("Введите грузинское слово:", reply_markup=_add_word_cancel_menu())


@router.message(AddWordForm.georgian, F.text == CANCEL_ADD_WORD_TEXT)
@router.message(AddWordForm.russian, F.text == CANCEL_ADD_WORD_TEXT)
@router.message(AddWordForm.topic, F.text == CANCEL_ADD_WORD_TEXT)
async def cancel_add_word_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Добавление слова отменено.", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(AddWordForm.georgian)
async def add_word_georgian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(georgian=message.text.strip())
    await state.set_state(AddWordForm.russian)
    await message.answer("Введите русский перевод:", reply_markup=_add_word_cancel_menu())


@router.message(AddWordForm.russian)
async def add_word_russian_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(russian=message.text.strip())
    await state.set_state(AddWordForm.topic)
    await message.answer("Введите тему слова (или '-' чтобы пропустить):", reply_markup=_add_word_cancel_menu())


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
            await message.answer(
                "Такое слово уже есть в словаре",
                reply_markup=get_main_menu(is_admin(message.from_user.id)),
            )
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
    await message.answer("Слово добавлено", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(LearnWordForm.answer)
async def learn_word_answer_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    word_id = data["word_id"]
    now = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        result = await session.execute(select(Word).where(Word.id == word_id))
        word = result.scalar_one_or_none()
        if word is None:
            await state.clear()
            await message.answer(
                "Слово не найдено. Попробуй снова.",
                reply_markup=get_main_menu(is_admin(message.from_user.id)),
            )
            return

        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )
            session.add(user)
            await session.flush()

        user_answer = _normalize_text(message.text)
        correct_answer = _normalize_text(word.russian)
        is_correct = user_answer == correct_answer

        progress_result = await session.execute(
            select(UserWordProgress).where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.word_id == word.id,
            )
        )
        progress = progress_result.scalar_one_or_none()
        if progress is None:
            progress = UserWordProgress(user_id=user.id, word_id=word.id)
            session.add(progress)
            progress.correct_count = 0
            progress.wrong_count = 0
            progress.level = 0
        else:
            if progress.correct_count is None:
                progress.correct_count = 0
            if progress.wrong_count is None:
                progress.wrong_count = 0
            if progress.level is None:
                progress.level = 0

        if is_correct:
            progress.correct_count += 1
            current_level = progress.level
            if current_level == 0:
                progress.next_review_at = now + timedelta(days=1)
            elif current_level == 1:
                progress.next_review_at = now + timedelta(days=3)
            elif current_level == 2:
                progress.next_review_at = now + timedelta(days=7)
            elif current_level == 3:
                progress.next_review_at = now + timedelta(days=14)
            else:
                progress.next_review_at = now + timedelta(days=30)
            progress.level = current_level + 1
        else:
            progress.wrong_count += 1
            progress.level = 0
            progress.next_review_at = now
        progress.last_answered_at = now
        await session.commit()

    if is_correct:
        await message.answer("✅ Верно", reply_markup=learn_menu)
    else:
        await message.answer(f"❌ Неверно. Правильный ответ: {word.russian}", reply_markup=learn_menu)


@router.message(F.text == "➡️ Следующее слово")
async def next_word_handler(message: Message, state: FSMContext) -> None:
    await _send_random_word(message, state)


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message) -> None:
    now = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        total_words_result = await session.execute(select(func.count(Word.id)))
        total_words = total_words_result.scalar_one()

        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()

        if user is None:
            trained_words = 0
            due_words = 0
            total_correct = 0
            total_wrong = 0
        else:
            trained_words_result = await session.execute(
                select(func.count(UserWordProgress.id)).where(UserWordProgress.user_id == user.id)
            )
            trained_words = trained_words_result.scalar_one()

            due_words_result = await session.execute(
                select(func.count(Word.id))
                .select_from(Word)
                .outerjoin(
                    UserWordProgress,
                    and_(
                        UserWordProgress.word_id == Word.id,
                        UserWordProgress.user_id == user.id,
                    ),
                )
                .where(
                    or_(
                        UserWordProgress.next_review_at.is_(None),
                        UserWordProgress.next_review_at <= now,
                    )
                )
            )
            due_words = due_words_result.scalar_one()

            answers_result = await session.execute(
                select(
                    func.coalesce(func.sum(UserWordProgress.correct_count), 0),
                    func.coalesce(func.sum(UserWordProgress.wrong_count), 0),
                ).where(UserWordProgress.user_id == user.id)
            )
            total_correct, total_wrong = answers_result.one()

    text = (
        "📊 Твоя статистика:\n\n"
        f"• Всего слов в базе: {total_words}\n"
        f"• Уже тренировал(а): {trained_words}\n"
        f"• Доступно к повторению сейчас: {due_words}\n"
        f"• Правильных ответов: {total_correct}\n"
        f"• Ошибок: {total_wrong}"
    )
    await message.answer(text)


@router.message(F.text == "⚙️ Настройки")
async def settings_handler(message: Message) -> None:
    await message.answer("Настройки пока в разработке.")
