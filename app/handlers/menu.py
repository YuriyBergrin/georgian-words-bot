import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy import select

from app.db.session import SessionLocal
from app.keyboards.training import (
    BACK_TO_MENU_TEXT,
    REPEAT_TOPIC_TEXT,
    TRAIN_ALL_WORDS_TEXT,
    TRAIN_BY_TOPIC_TEXT,
    topic_completed_menu,
    topics_menu,
    training_mode_menu,
    translation_options_menu,
)
from app.keyboards.learn_menu import learn_menu
from app.keyboards.main_menu import get_main_menu
from app.models.word import Word
from app.services.admin_service import is_admin
from app.services.stats_service import StatsService
from app.services.topic_service import TopicService
from app.services.training_service import TrainingService
from app.services.word_service import WordService

router = Router()
CANCEL_ADD_WORD_TEXT = "❌ Отмена"


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


async def _send_random_word(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    selected_topic = data.get("selected_topic")
    repeat_word_id = data.get("repeat_word_id")
    repeat_direction = data.get("repeat_direction")
    repeat_remaining = data.get("repeat_remaining", 0)
    word: Word | None = None
    question_text = ""
    expected_answer = ""
    direction = ""
    is_choice_question = False
    options: list[str] = []

    async with SessionLocal() as session:
        training_service = TrainingService(session)
        user = await training_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        if repeat_word_id and repeat_direction and repeat_remaining <= 0:
            result = await session.execute(select(Word).where(Word.id == repeat_word_id))
            repeat_word = result.scalar_one_or_none()
            if repeat_word is not None:
                word = repeat_word
                direction = repeat_direction
                question_text, expected_answer = training_service.build_question(word, direction=direction)
                is_choice_question = direction == TrainingService.DIRECTION_GE_RU or (
                    direction == TrainingService.DIRECTION_RU_GE and random.choice([True, False])
                )
                if is_choice_question:
                    answer_language = "russian" if direction == TrainingService.DIRECTION_GE_RU else "georgian"
                    options = await training_service.build_translation_options(
                        correct_answer=expected_answer,
                        word_id=word.id,
                        answer_language=answer_language,
                    )
                await state.update_data(repeat_word_id=None, repeat_direction=None, repeat_remaining=0)

        if word is None:
            exclude_word_id = repeat_word_id if repeat_word_id and repeat_remaining > 0 else None
            word_with_direction = await training_service.get_random_word_with_direction(
                user_id=user.id,
                topic=selected_topic,
                exclude_word_id=exclude_word_id,
            )
            if word_with_direction is None and repeat_word_id and repeat_direction:
                result = await session.execute(select(Word).where(Word.id == repeat_word_id))
                repeat_word = result.scalar_one_or_none()
                if repeat_word is not None:
                    word_with_direction = (repeat_word, repeat_direction)
                    await state.update_data(repeat_word_id=None, repeat_direction=None, repeat_remaining=0)

            if word_with_direction is not None:
                word, direction = word_with_direction
                question_text, expected_answer = training_service.build_question(word, direction=direction)
                is_choice_question = direction == TrainingService.DIRECTION_GE_RU or (
                    direction == TrainingService.DIRECTION_RU_GE and random.choice([True, False])
                )
                if is_choice_question:
                    answer_language = "russian" if direction == TrainingService.DIRECTION_GE_RU else "georgian"
                    options = await training_service.build_translation_options(
                        correct_answer=expected_answer,
                        word_id=word.id,
                        answer_language=answer_language,
                    )
                if repeat_word_id and repeat_direction and repeat_remaining > 0:
                    await state.update_data(repeat_remaining=repeat_remaining - 1)
        await session.commit()

    if word is None:
        if selected_topic is None:
            await message.answer("Пока нет слов для повторения.", reply_markup=learn_menu)
        else:
            await message.answer(
                f"Вы прошли все слова на тему «{selected_topic}».",
                reply_markup=topic_completed_menu(),
            )
        return

    await state.set_state(LearnWordForm.answer)
    await state.update_data(
        word_id=word.id,
        question_direction=direction,
        expected_answer=expected_answer,
        question_type="choice" if is_choice_question else "text",
    )

    if is_choice_question:
        await message.answer(
            f"Переведи слово: {question_text}",
            reply_markup=translation_options_menu(options),
        )
    else:
        await message.answer(f"Переведи слово: {question_text}", reply_markup=learn_menu)


@router.message(F.text == "📚 Учить слова")
async def learn_words_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(LearnWordForm.mode)
    await message.answer("Выбери режим тренировки:", reply_markup=training_mode_menu())


@router.message(LearnWordForm.mode, F.text == TRAIN_ALL_WORDS_TEXT)
async def learn_all_words_mode_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(selected_topic=None)
    await _send_random_word(message, state)


@router.message(LearnWordForm.mode, F.text == TRAIN_BY_TOPIC_TEXT)
async def learn_by_topic_mode_handler(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        topics = await TopicService(session).list_topics_with_words()

    if not topics:
        await state.set_state(LearnWordForm.mode)
        await message.answer("Темы пока не добавлены", reply_markup=training_mode_menu())
        return

    await state.set_state(LearnWordForm.topic)
    await message.answer("Выбери тему:", reply_markup=topics_menu(topics))


@router.message(LearnWordForm.topic)
async def learn_topic_selected_handler(message: Message, state: FSMContext) -> None:
    topic_name = message.text.strip()
    if topic_name == BACK_TO_MENU_TEXT:
        await state.clear()
        await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))
        return

    async with SessionLocal() as session:
        topic_service = TopicService(session)
        topic_exists = await topic_service.topic_exists_with_words(topic_name)
        topics = await topic_service.list_topics_with_words()

    if not topic_exists:
        await message.answer("Выбери тему из списка.", reply_markup=topics_menu(topics))
        return

    await state.update_data(selected_topic=topic_name)
    await _send_random_word(message, state)


@router.message(LearnWordForm.mode, F.text == BACK_TO_MENU_TEXT)
@router.message(LearnWordForm.topic, F.text == BACK_TO_MENU_TEXT)
async def back_from_training_mode_to_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(F.text == REPEAT_TOPIC_TEXT)
async def repeat_topic_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    selected_topic = data.get("selected_topic")
    if not selected_topic:
        await state.clear()
        await message.answer("Сначала выбери режим тренировки.", reply_markup=training_mode_menu())
        return

    async with SessionLocal() as session:
        training_service = TrainingService(session)
        user = await training_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await training_service.reset_topic_for_repeat(user_id=user.id, topic=selected_topic)
        await session.commit()

    await _send_random_word(message, state)


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


@router.message(LearnWordForm.answer, F.text == "🏠 Главное меню")
async def back_to_main_menu_from_answer_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(LearnWordForm.answer)
async def learn_word_answer_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    word_id = data["word_id"]
    question_direction = data.get("question_direction", TrainingService.DIRECTION_GE_RU)
    expected_answer_value = data.get("expected_answer")
    question_type = data.get("question_type", "text")

    async with SessionLocal() as session:
        training_service = TrainingService(session)
        result = await session.execute(select(Word).where(Word.id == word_id))
        word = result.scalar_one_or_none()
        if word is None:
            await state.clear()
            await message.answer(
                "Слово не найдено. Попробуй снова.",
                reply_markup=get_main_menu(is_admin(message.from_user.id)),
            )
            return

        user = await training_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        user_answer = _normalize_text(message.text)
        correct_answer = _normalize_text(expected_answer_value or word.russian)
        is_correct = user_answer == correct_answer

        await training_service.apply_answer(
            user=user,
            word=word,
            direction=question_direction,
            is_correct=is_correct,
            is_choice=question_type == "choice",
        )
        await session.commit()

    if not is_correct:
        await state.update_data(
            repeat_word_id=word_id,
            repeat_direction=question_direction,
            repeat_remaining=1,
        )

    if is_correct:
        await message.answer("✅ Верно", reply_markup=learn_menu)
    else:
        correct_text = expected_answer_value or word.russian
        await message.answer(f"❌ Неверно. Правильный ответ: {correct_text}", reply_markup=learn_menu)
    await _send_random_word(message, state)


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


@router.message(F.text == "⚙️ Настройки")
async def settings_handler(message: Message) -> None:
    await message.answer("Настройки пока в разработке.")
