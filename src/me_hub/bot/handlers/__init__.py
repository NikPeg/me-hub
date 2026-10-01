from aiogram import Router

from me_hub.bot.handlers import checkin, common, habits, settings


def build_router() -> Router:
    router = Router(name="root")
    router.include_routers(
        common.router, checkin.router, habits.router, settings.router, common.fallback_router
    )
    return router
