from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
            existing_user = result.scalar_one()
            return existing_user

    async def get_or_create_user_in_session(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        self.session.add(user)
        try:
            await self.session.flush()
            return user
        except IntegrityError:
            await self.session.rollback()
            result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
            existing_user = result.scalar_one()
            return existing_user

    async def touch_daily_streak(self, user: User, today: date | None = None) -> None:
        current = today or date.today()
        if user.last_active_date is None:
            user.streak_days = 1
            user.last_active_date = current
            return

        if user.last_active_date == current:
            return

        if user.last_active_date == current - timedelta(days=1):
            user.streak_days = (user.streak_days or 0) + 1
        else:
            user.streak_days = 1
        user.last_active_date = current
