import random
from datetime import datetime

from app.contracts.training_dto import NextQuestionResult, SubmitAnswerResult
from app.infrastructure.db.uow import UnitOfWork
from app.models.word import Word
from app.services.training_service import TrainingService


class TrainingFlowService:
    async def list_topics_with_words(self) -> list[str]:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            return await uow.topics.list_topics_with_words()

    async def topic_exists_with_words(self, topic_name: str) -> tuple[bool, list[str]]:
        async with UnitOfWork() as uow:
            assert uow.topics is not None
            exists = await uow.topics.topic_exists_with_words(topic_name)
            topics = await uow.topics.list_topics_with_words()
            return exists, topics

    async def reset_topic_for_repeat(
        self, telegram_id: int, username: str | None, first_name: str | None, topic: str
    ) -> None:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            assert uow.words is not None
            session = uow.session
            training_service = TrainingService(session)
            user = await training_service.get_or_create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            await training_service.reset_topic_for_repeat(user_id=user.id, topic=topic)
            await uow.commit()

    async def next_question(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        selected_topic: str | None,
        repeat_word_id: int | None,
        repeat_direction: str | None,
        repeat_remaining: int,
    ) -> NextQuestionResult:
        word: Word | None = None
        direction = ""
        question_text = ""
        expected_answer = ""
        is_choice_question = False
        options: list[str] = []
        next_repeat_remaining = repeat_remaining
        clear_repeat_state = False

        async with UnitOfWork() as uow:
            assert uow.session is not None
            session = uow.session
            training_service = TrainingService(session)
            user = await training_service.get_or_create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )

            if repeat_word_id and repeat_direction and repeat_remaining <= 0:
                repeat_word = await uow.words.get_by_id(repeat_word_id)
                if repeat_word is not None:
                    word = repeat_word
                    direction = repeat_direction
                    question_text, expected_answer, is_choice_question, options = await self._prepare_question_payload(
                        training_service, word, direction
                    )
                    clear_repeat_state = True

            if word is None:
                exclude_word_id = repeat_word_id if repeat_word_id and repeat_remaining > 0 else None
                word_with_direction = await training_service.get_random_word_with_direction(
                    user_id=user.id,
                    topic=selected_topic,
                    exclude_word_id=exclude_word_id,
                )
                if word_with_direction is None and repeat_word_id and repeat_direction:
                    repeat_word = await uow.words.get_by_id(repeat_word_id)
                    if repeat_word is not None:
                        word_with_direction = (repeat_word, repeat_direction)
                        clear_repeat_state = True

                if word_with_direction is not None:
                    word, direction = word_with_direction
                    question_text, expected_answer, is_choice_question, options = await self._prepare_question_payload(
                        training_service, word, direction
                    )
                    if repeat_word_id and repeat_direction and repeat_remaining > 0:
                        next_repeat_remaining = repeat_remaining - 1
            await uow.commit()

        if word is None:
            return NextQuestionResult(status="none", selected_topic=selected_topic)

        return NextQuestionResult(
            status="question",
            word_id=word.id,
            direction=direction,
            question_text=question_text,
            expected_answer=expected_answer,
            question_type="choice" if is_choice_question else "text",
            options=options,
            next_repeat_remaining=next_repeat_remaining,
            clear_repeat_state=clear_repeat_state,
            reason="repeat_after_error" if repeat_word_id and repeat_remaining <= 0 else "normal",
        )

    async def submit_answer(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        word_id: int,
        question_direction: str,
        expected_answer_value: str | None,
        question_type: str,
        user_answer_text: str,
        normalize_func,
    ) -> SubmitAnswerResult:
        level_before = None
        streak_before = None
        level_after = None
        streak_after = None
        next_review_after: datetime | None = None

        async with UnitOfWork() as uow:
            assert uow.session is not None
            assert uow.words is not None
            session = uow.session
            training_service = TrainingService(session)
            word = await uow.words.get_by_id(word_id)
            if word is None:
                return SubmitAnswerResult(status="not_found")

            user = await training_service.get_or_create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            progress_before = await training_service.scoring.get_progress(user.id, word.id, question_direction)
            if progress_before is not None:
                level_before = progress_before.level
                streak_before = progress_before.streak_correct

            user_answer = normalize_func(user_answer_text)
            correct_answer = normalize_func(expected_answer_value or word.russian)
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
            await uow.commit()

        return SubmitAnswerResult(
            status="ok",
            is_correct=is_correct,
            correct_text=expected_answer_value or word.russian,
            level_before=level_before,
            streak_before=streak_before,
            level_after=level_after,
            streak_after=streak_after,
            next_review_after=next_review_after,
            word_id=word_id,
            question_direction=question_direction,
            question_type=question_type,
        )

    @staticmethod
    async def _prepare_question_payload(
        training_service: TrainingService, word: Word, direction: str
    ) -> tuple[str, str, bool, list[str]]:
        question_text, expected_answer = training_service.build_question(word, direction=direction)
        is_choice_question = direction == TrainingService.DIRECTION_GE_RU or (
            direction == TrainingService.DIRECTION_RU_GE and random.choice([True, False])
        )
        options: list[str] = []
        if is_choice_question:
            answer_language = "russian" if direction == TrainingService.DIRECTION_GE_RU else "georgian"
            options = await training_service.build_translation_options(
                correct_answer=expected_answer,
                word_id=word.id,
                answer_language=answer_language,
            )
        return question_text, expected_answer, is_choice_question, options
