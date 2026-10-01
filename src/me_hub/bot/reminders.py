import logging
from collections.abc import Callable, Coroutine
from datetime import time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from me_hub.bot import texts
from me_hub.bot.views import View, checkin_view
from me_hub.core.habits import has_checks_on, local_today
from me_hub.core.models import User

logger = logging.getLogger(__name__)

MISFIRE_GRACE_SECONDS = 60 * 60


class MessageSender(Protocol):
    async def send_message(
        self, chat_id: int | str, text: str, *, reply_markup: InlineKeyboardMarkup | None = None
    ) -> object: ...


async def send_evening_checkin(
    sender: MessageSender, session_factory: async_sessionmaker[AsyncSession], user_id: int
) -> None:
    async with session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            return
        view = await checkin_view(session, user, local_today(user), intro=texts.EVENING_INTRO)
    if view is not None:
        await _send(sender, user_id, view)


async def send_morning_reminder(
    sender: MessageSender, session_factory: async_sessionmaker[AsyncSession], user_id: int
) -> None:
    """Asks to fill in yesterday when nothing was marked for it."""
    async with session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            return
        yesterday = local_today(user) - timedelta(days=1)
        if await has_checks_on(session, user_id, yesterday):
            return
        view = await checkin_view(session, user, yesterday, intro=texts.MORNING_INTRO)
    if view is not None:
        await _send(sender, user_id, view)


type ReminderJob = Callable[
    [MessageSender, async_sessionmaker[AsyncSession], int], Coroutine[None, None, None]
]


async def _send(sender: MessageSender, chat_id: int, view: View) -> None:
    try:
        await sender.send_message(chat_id, view.text, reply_markup=view.markup)
    except TelegramAPIError:
        logger.exception("Failed to send a reminder to %s", chat_id)


class ReminderScheduler:
    """Keeps one evening check-in and one morning reminder job per user, in the user's timezone.

    Jobs live in memory and are rebuilt from the database on startup."""

    def __init__(
        self,
        scheduler: AsyncIOScheduler,
        sender: MessageSender,
        session_factory: async_sessionmaker[AsyncSession],
        morning_time: time,
    ) -> None:
        self._scheduler = scheduler
        self._sender = sender
        self._session_factory = session_factory
        self._morning_time = morning_time

    @staticmethod
    def evening_job_id(user_id: int) -> str:
        return f"evening:{user_id}"

    @staticmethod
    def morning_job_id(user_id: int) -> str:
        return f"morning:{user_id}"

    def schedule(self, user: User) -> None:
        zone = user.zone
        self._add_daily_job(
            self.evening_job_id(user.id), send_evening_checkin, user.reminder_time, zone, user.id
        )
        self._add_daily_job(
            self.morning_job_id(user.id), send_morning_reminder, self._morning_time, zone, user.id
        )
        logger.info(
            "Scheduled reminders for %s at %s and %s (%s)",
            user.id,
            user.reminder_time,
            self._morning_time,
            user.timezone,
        )

    def _add_daily_job(
        self, job_id: str, func: ReminderJob, at: time, zone: ZoneInfo, user_id: int
    ) -> None:
        self._scheduler.add_job(
            func,
            CronTrigger(hour=at.hour, minute=at.minute, timezone=zone),
            id=job_id,
            replace_existing=True,
            kwargs={
                "sender": self._sender,
                "session_factory": self._session_factory,
                "user_id": user_id,
            },
            misfire_grace_time=MISFIRE_GRACE_SECONDS,
            coalesce=True,
            max_instances=1,
        )
