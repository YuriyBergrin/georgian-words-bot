from aiogram import Router

from app.handlers.admin_manage import router as admin_manage_router
from app.handlers.admin_stats import router as admin_stats_router
from app.handlers.admin_words import router as admin_words_router
from app.handlers.common import router as common_router
from app.handlers.start import router as start_router
from app.handlers.training import router as training_router

router = Router()
router.include_router(start_router)
router.include_router(admin_manage_router)
router.include_router(common_router)
router.include_router(training_router)
router.include_router(admin_words_router)
router.include_router(admin_stats_router)

__all__ = ["router"]
