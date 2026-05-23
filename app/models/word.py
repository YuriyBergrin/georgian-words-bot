from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.user_word_progress import UserWordProgress


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    georgian: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    russian: Mapped[str] = mapped_column(String(255), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    progress: Mapped[list["UserWordProgress"]] = relationship(back_populates="word", cascade="all, delete-orphan")
    topic: Mapped["Topic | None"] = relationship(back_populates="words")
