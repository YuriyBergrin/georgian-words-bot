import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select

from app.db.session import SessionLocal
from app.handlers.states import LearnWordForm
from app.handlers.common_helpers import normalize_text
from app.keyboards.learn_menu import learn_menu
from app.keyboards.main_menu import get_main_menu
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
from app.models.word import Word
from app.services.admin_service import is_admin
from app.services.topic_service import TopicService
from app.services.training_service import TrainingService

router = Router()


async def send_random_word(message: Message, state: FSMContext) -> None:
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
        logger.info(
            "word_selected_none user_id={} topic={} repeat_word_id={} repeat_remaining={}",
            message.from_user.id,
            selected_topic,
            repeat_word_id,
            repeat_remaining,
        )
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
    logger.info(
        "word_selected user_id={} word_id={} topic={} direction={} question_type={} reason={}",
        message.from_user.id,
        word.id,
        selected_topic,
        direction,
        "choice" if is_choice_question else "text",
        "repeat_after_error" if repeat_word_id and repeat_remaining <= 0 else "normal",
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
    logger.info("state_transition user_id={} from_state=* to_state={}", message.from_user.id, LearnWordForm.mode.state)
    await state.set_state(LearnWordForm.mode)
    await message.answer("Выбери режим тренировки:", reply_markup=training_mode_menu())


@router.message(LearnWordForm.mode, F.text == TRAIN_ALL_WORDS_TEXT)
async def learn_all_words_mode_handler(message: Message, state: FSMContext) -> None:
    logger.info("training_mode_selected user_id={} mode=all_words", message.from_user.id)
    await state.update_data(selected_topic=None)
    await send_random_word(message, state)


@router.message(LearnWordForm.mode, F.text == TRAIN_BY_TOPIC_TEXT)
async def learn_by_topic_mode_handler(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        topics = await TopicService(session).list_topics_with_words()

    if not topics:
        logger.info("training_topics_empty user_id={}", message.from_user.id)
        await state.set_state(LearnWordForm.mode)
        await message.answer("Темы пока не добавлены", reply_markup=training_mode_menu())
        return

    logger.info("state_transition user_id={} from_state=* to_state={}", message.from_user.id, LearnWordForm.topic.state)
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
        logger.info("training_topic_invalid user_id={} topic={}", message.from_user.id, topic_name)
        await message.answer("Выбери тему из списка.", reply_markup=topics_menu(topics))
        return

    logger.info("training_topic_selected user_id={} topic={}", message.from_user.id, topic_name)
    await state.update_data(selected_topic=topic_name)
    await send_random_word(message, state)


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
        logger.info("repeat_topic_without_selected user_id={}", message.from_user.id)
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

    await send_random_word(message, state)
    logger.info("repeat_topic user_id={} topic={}", message.from_user.id, selected_topic)


@router.message(LearnWordForm.answer, F.text == "🏠 Главное меню")
async def back_to_main_menu_from_answer_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(LearnWordForm.answer, F.text == BACK_TO_MENU_TEXT)
async def back_to_main_menu_from_answer_back_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_menu(is_admin(message.from_user.id)))


@router.message(LearnWordForm.answer)
async def learn_word_answer_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    word_id = data["word_id"]
    question_direction = data.get("question_direction", TrainingService.DIRECTION_GE_RU)
    expected_answer_value = data.get("expected_answer")
    question_type = data.get("question_type", "text")

    level_before = None
    streak_before = None
    level_after = None
    streak_after = None
    next_review_after = None

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
        progress_before = await training_service.scoring.get_progress(user.id, word.id, question_direction)
        if progress_before is not None:
            level_before = progress_before.level
            streak_before = progress_before.streak_correct

        user_answer = normalize_text(message.text)
        correct_answer = normalize_text(expected_answer_value or word.russian)
        is_correct = user_answer == correct_answer

        await training_service.apply_answer(
            user=user,
            word=word,
            direction=question_direction,
            is_correct=is_correct,
            is_choice=question_type == "choice",
        )
        progress = await training_service.scoring.get_progress(user.id, word.id, question_direction)
        if progress is not None:
            level_after = progress.level
            streak_after = progress.streak_correct
            next_review_after = progress.next_review_at
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
    logger.info(
        "answer_result user_id={} word_id={} direction={} question_type={} is_correct={} level_before={} level_after={} streak_before={} streak_after={} next_review_at={}",
        message.from_user.id,
        word_id,
        question_direction,
        question_type,
        is_correct,
        level_before,
        level_after,
        streak_before,
        streak_after,
        next_review_after,
    )
    await send_random_word(message, state)
