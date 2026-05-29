from app.infrastructure.db.uow import UnitOfWork
from app.services.admin_service import AdminService


class AccessService:
    async def is_admin_user(self, telegram_id: int) -> bool:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            return await AdminService(uow.session).is_admin(telegram_id)
