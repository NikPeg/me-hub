import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from me_hub.bot import texts
from me_hub.bot.config import BotSettings
from me_hub.bot.handlers import build_router
from me_hub.bot.middlewares import DatabaseMiddleware, OwnerOnlyMiddleware
from me_hub.bot.reminders import ReminderScheduler
from me_hub.core.db import create_engine, create_session_factory
from me_hub.core.habits import ensure_user

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command=command, description=description)
    for command, description in texts.COMMAND_DESCRIPTIONS.items()
]


async def handle_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled error while processing an update", exc_info=event.exception)
    update = event.update
    with suppress(TelegramAPIError):
        if update.callback_query is not None:
            await update.callback_query.answer(texts.SOMETHING_WENT_WRONG, show_alert=True)
        elif update.message is not None:
            await update.message.answer(texts.SOMETHING_WENT_WRONG)
    return True


def create_dispatcher(
    settings: BotSettings,
    session_factory: async_sessionmaker[AsyncSession],
    reminders: ReminderScheduler,
) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage(), config=settings, reminders=reminders)
    dispatcher.update.outer_middleware(OwnerOnlyMiddleware(settings.telegram_owner_id))
    dispatcher.update.middleware(DatabaseMiddleware(session_factory, settings))
    dispatcher.include_router(build_router())
    dispatcher.errors.register(handle_error)
    return dispatcher


async def run(settings: BotSettings) -> None:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    scheduler = AsyncIOScheduler()
    reminders = ReminderScheduler(scheduler, bot, session_factory, settings.morning_reminder_time)
    dispatcher = create_dispatcher(settings, session_factory, reminders)
    try:
        async with session_factory() as session:
            owner = await ensure_user(
                session,
                settings.telegram_owner_id,
                settings.default_timezone,
                settings.default_reminder_time,
            )
            await session.commit()
        reminders.schedule(owner)
        scheduler.start()
        await bot.set_my_commands(COMMANDS)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await bot.session.close()
        await engine.dispose()
