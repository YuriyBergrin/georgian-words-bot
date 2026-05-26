from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.word import Word
from app.services.training_constants import DIRECTION_GE_RU, DIRECTION_RU_GE
from app.services.training_scheduling_service import TrainingSchedulingService
from app.services.training_scoring_service import TrainingScoringService
from app.services.training_selection_service import TrainingSelectionService
from app.services.user_service import UserService


class TrainingService:
    DIRECTION_GE_RU = DIRECTION_GE_RU
    DIRECTION_RU_GE = DIRECTION_RU_GE

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_service = UserService(session)
        self.selection = TrainingSelectionService(session)
        self.scheduling = TrainingSchedulingService(session)
        self.scoring = TrainingScoringService(session)

    async def get_or_create_user(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        user = await self.user_service.get_or_create_user_in_session(telegram_id, username, first_name)
        await self.user_service.touch_daily_streak(user)
        return user

    async def get_random_word(
        self,
        user_id: int,
        topic: str | None = None,
        direction: str = DIRECTION_GE_RU,
        exclude_word_id: int | None = None,
    ) -> Word | None:
        return await self.selection.get_random_word(
            user_id=user_id,
            topic=topic,
            direction=direction,
            exclude_word_id=exclude_word_id,
        )

    async def get_random_word_with_direction(
        self, user_id: int, topic: str | None = None, exclude_word_id: int | None = None
    ) -> tuple[Word, str] | None:
        return await self.selection.get_random_word_with_direction(
            user_id=user_id,
            topic=topic,
            exclude_word_id=exclude_word_id,
        )

    def build_question(self, word: Word, direction: str) -> tuple[str, str]:
        return self.selection.build_question(word, direction)

    async def build_translation_options(self, correct_answer: str, word_id: int, answer_language: str) -> list[str]:
        return await self.selection.build_translation_options(correct_answer, word_id, answer_language)

    async def apply_answer(self, user: User, word: Word, direction: str, is_correct: bool, is_choice: bool) -> None:
        await self.scoring.apply_answer(user, word, direction, is_correct, is_choice)

    async def reset_topic_for_repeat(self, user_id: int, topic: str) -> None:
        await self.scheduling.reset_topic_for_repeat(user_id, topic)
