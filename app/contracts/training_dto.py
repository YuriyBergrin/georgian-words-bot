from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class NextQuestionResult:
    status: str
    selected_topic: str | None = None
    word_id: int | None = None
    direction: str = ""
    question_text: str = ""
    expected_answer: str = ""
    question_type: str = "text"
    options: list[str] | None = None
    next_repeat_remaining: int = 0
    clear_repeat_state: bool = False
    reason: str = "normal"


@dataclass(slots=True)
class SubmitAnswerResult:
    status: str
    is_correct: bool = False
    correct_text: str = ""
    level_before: int | None = None
    streak_before: int | None = None
    level_after: int | None = None
    streak_after: int | None = None
    next_review_after: datetime | None = None
    word_id: int | None = None
    question_direction: str = ""
    question_type: str = "text"
