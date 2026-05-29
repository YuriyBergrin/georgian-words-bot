from app.infrastructure.db.uow import UnitOfWork
from app.services.admin_service import AdminService


class AdminManageService:
    @staticmethod
    def is_bootstrap_admin(telegram_id: int) -> bool:
        return AdminService.is_bootstrap_admin(telegram_id)

    async def list_admin_ids(self) -> list[int]:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            return await AdminService(uow.session).list_admin_ids()

    async def add_admin(self, telegram_id: int) -> bool:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            service = AdminService(uow.session)
            created = await service.add_admin(telegram_id)
            if created:
                await uow.commit()
            return created

    async def remove_admin(self, telegram_id: int) -> tuple[bool, str | None]:
        async with UnitOfWork() as uow:
            assert uow.session is not None
            service = AdminService(uow.session)
            removed, reason = await service.remove_admin(telegram_id)
            if removed:
                await uow.commit()
            return removed, reason
