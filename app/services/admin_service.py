from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.admin import Admin


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def is_bootstrap_admin(telegram_id: int) -> bool:
        return telegram_id in settings.admin_ids_set

    async def is_admin(self, telegram_id: int) -> bool:
        if self.is_bootstrap_admin(telegram_id):
            return True
        result = await self.session.execute(select(Admin.id).where(Admin.telegram_id == telegram_id))
        return result.scalar_one_or_none() is not None

    async def list_admin_ids(self) -> list[int]:
        result = await self.session.execute(select(Admin.telegram_id).order_by(Admin.telegram_id.asc()))
        ids = list(result.scalars().all())
        return sorted(set(ids).union(settings.admin_ids_set))

    async def add_admin(self, telegram_id: int) -> bool:
        result = await self.session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        if result.scalar_one_or_none() is not None:
            return False
        self.session.add(Admin(telegram_id=telegram_id))
        return True

    async def remove_admin(self, telegram_id: int) -> tuple[bool, str | None]:
        if self.is_bootstrap_admin(telegram_id):
            return False, "Нельзя удалить bootstrap-суперадмина из .env"
        result = await self.session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return False, "Админ не найден"
        await self.session.delete(admin)
        return True, None
