from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    georgian: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    russian: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    progress: Mapped[list["UserWordProgress"]] = relationship(back_populates="word", cascade="all, delete-orphan")
