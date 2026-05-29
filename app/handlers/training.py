from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.handlers.common_helpers import clear_and_reply_main_menu, normalize_text
from app.handlers.states import LearnWordForm
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
from app.middlewares.services_middleware import AppServices
from app.services.training_service import TrainingService

router = Router()


async def send_random_word(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    selected_topic = data.get("selected_topic")
    repeat_word_id = data.get("repeat_word_id")
    repeat_direction = data.get("repeat_direction")
    repeat_remaining = data.get("repeat_remaining", 0)
    question = await services.training_flow.next_question(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        selected_topic=selected_topic,
        repeat_word_id=repeat_word_id,
        repeat_direction=repeat_direction,
        repeat_remaining=repeat_remaining,
    )

    if question.status == "none":
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

    if question.clear_repeat_state:
        await state.update_data(repeat_word_id=None, repeat_direction=None, repeat_remaining=0)
    elif question.next_repeat_remaining != repeat_remaining:
        await state.update_data(repeat_remaining=question.next_repeat_remaining)

    await state.set_state(LearnWordForm.answer)
    await state.update_data(
        word_id=question.word_id,
        question_direction=question.direction,
        expected_answer=question.expected_answer,
        question_type=question.question_type,
    )
    logger.info(
        "word_selected user_id={} word_id={} topic={} direction={} question_type={} reason={}",
        message.from_user.id,
        question.word_id,
        selected_topic,
        question.direction,
        question.question_type,
        question.reason,
    )

    if question.question_type == "choice":
        await message.answer(
            f"Переведи слово: {question.question_text}",
            reply_markup=translation_options_menu(question.options or []),
        )
    else:
        await message.answer(f"Переведи слово: {question.question_text}", reply_markup=learn_menu)


@router.message(F.text == "📚 Учить слова")
async def learn_words_handler(message: Message, state: FSMContext) -> None:
    logger.info("state_transition user_id={} from_state=* to_state={}", message.from_user.id, LearnWordForm.mode.state)
    await state.set_state(LearnWordForm.mode)
    await message.answer("Выбери режим тренировки:", reply_markup=training_mode_menu())


@router.message(LearnWordForm.mode, F.text == TRAIN_ALL_WORDS_TEXT)
async def learn_all_words_mode_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    logger.info("training_mode_selected user_id={} mode=all_words", message.from_user.id)
    await state.update_data(selected_topic=None)
    await send_random_word(message, state, services)


@router.message(LearnWordForm.mode, F.text == TRAIN_BY_TOPIC_TEXT)
async def learn_by_topic_mode_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    topics = await services.training_flow.list_topics_with_words()

    if not topics:
        logger.info("training_topics_empty user_id={}", message.from_user.id)
        await state.set_state(LearnWordForm.mode)
        await message.answer("Темы пока не добавлены", reply_markup=training_mode_menu())
        return

    logger.info("state_transition user_id={} from_state=* to_state={}", message.from_user.id, LearnWordForm.topic.state)
    await state.set_state(LearnWordForm.topic)
    await message.answer("Выбери тему:", reply_markup=topics_menu(topics))


@router.message(LearnWordForm.topic)
async def learn_topic_selected_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    topic_name = message.text.strip()
    if topic_name == BACK_TO_MENU_TEXT:
        await clear_and_reply_main_menu(
            message, state, is_admin=await services.access.is_admin_user(message.from_user.id)
        )
        return

    topic_exists, topics = await services.training_flow.topic_exists_with_words(topic_name)

    if not topic_exists:
        logger.info("training_topic_invalid user_id={} topic={}", message.from_user.id, topic_name)
        await message.answer("Выбери тему из списка.", reply_markup=topics_menu(topics))
        return

    logger.info("training_topic_selected user_id={} topic={}", message.from_user.id, topic_name)
    await state.update_data(selected_topic=topic_name)
    await send_random_word(message, state, services)


@router.message(LearnWordForm.mode, F.text == BACK_TO_MENU_TEXT)
@router.message(LearnWordForm.topic, F.text == BACK_TO_MENU_TEXT)
async def back_from_training_mode_to_menu_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    await clear_and_reply_main_menu(message, state, is_admin=await services.access.is_admin_user(message.from_user.id))


@router.message(F.text == REPEAT_TOPIC_TEXT)
async def repeat_topic_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    selected_topic = data.get("selected_topic")
    if not selected_topic:
        logger.info("repeat_topic_without_selected user_id={}", message.from_user.id)
        await state.clear()
        await message.answer("Сначала выбери режим тренировки.", reply_markup=training_mode_menu())
        return

    await services.training_flow.reset_topic_for_repeat(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        topic=selected_topic,
    )

    await send_random_word(message, state, services)
    logger.info("repeat_topic user_id={} topic={}", message.from_user.id, selected_topic)


@router.message(LearnWordForm.answer, F.text == "🏠 Главное меню")
async def back_to_main_menu_from_answer_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    await clear_and_reply_main_menu(message, state, is_admin=await services.access.is_admin_user(message.from_user.id))


@router.message(LearnWordForm.answer, F.text == BACK_TO_MENU_TEXT)
async def back_to_main_menu_from_answer_back_handler(
    message: Message, state: FSMContext, services: AppServices
) -> None:
    await clear_and_reply_main_menu(message, state, is_admin=await services.access.is_admin_user(message.from_user.id))


@router.message(LearnWordForm.answer)
async def learn_word_answer_handler(message: Message, state: FSMContext, services: AppServices) -> None:
    data = await state.get_data()
    word_id = data["word_id"]
    question_direction = data.get("question_direction", TrainingService.DIRECTION_GE_RU)
    expected_answer_value = data.get("expected_answer")
    question_type = data.get("question_type", "text")

    submit_result = await services.training_flow.submit_answer(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        word_id=word_id,
        question_direction=question_direction,
        expected_answer_value=expected_answer_value,
        question_type=question_type,
        user_answer_text=message.text or "",
        normalize_func=normalize_text,
    )
    if submit_result.status == "not_found":
        await state.clear()
        await message.answer(
            "Слово не найдено. Попробуй снова.",
            reply_markup=get_main_menu(await services.access.is_admin_user(message.from_user.id)),
        )
        return
    is_correct = submit_result.is_correct

    if not is_correct:
        await state.update_data(
            repeat_word_id=word_id,
            repeat_direction=question_direction,
            repeat_remaining=1,
        )

    if is_correct:
        await message.answer("✅ Верно", reply_markup=learn_menu)
    else:
        await message.answer(f"❌ Неверно. Правильный ответ: {submit_result.correct_text}", reply_markup=learn_menu)
    logger.info(
        "answer_result user_id={} word_id={} direction={} question_type={} is_correct={} level_before={} level_after={} streak_before={} streak_after={} next_review_at={}",
        message.from_user.id,
        word_id,
        question_direction,
        question_type,
        is_correct,
        submit_result.level_before,
        submit_result.level_after,
        submit_result.streak_before,
        submit_result.streak_after,
        submit_result.next_review_after,
    )
    await send_random_word(message, state, services)
