from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProgressStatus(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    KNOWN = "known"


class UserWordProgress(Base):
    __tablename__ = "user_word_progress"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_user_word"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), index=True)
    status: Mapped[ProgressStatus] = mapped_column(
        SQLEnum(ProgressStatus, name="progress_status"), default=ProgressStatus.NEW
    )
    correct_answers: Mapped[int] = mapped_column(default=0)
    wrong_answers: Mapped[int] = mapped_column(default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="progress")
    word: Mapped["Word"] = relationship(back_populates="progress")
