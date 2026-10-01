from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import time, timedelta
from zoneinfo import ZoneInfo

import pytest
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import SendMessage
from aiogram.types import InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from me_hub.bot import texts
from me_hub.bot.reminders import ReminderScheduler, send_evening_checkin, send_morning_reminder
from me_hub.core.habits import add_habit, local_today, toggle_check
from me_hub.core.models import User


@dataclass
class SentMessage:
    chat_id: int | str
    text: str
    reply_markup: InlineKeyboardMarkup | None


@dataclass
class FakeSender:
    sent: list[SentMessage] = field(default_factory=list)
    fail: bool = False

    async def send_message(
        self, chat_id: int | str, text: str, *, reply_markup: InlineKeyboardMarkup | None = None
    ) -> object:
        if self.fail:
            raise TelegramNetworkError(method=SendMessage(chat_id=chat_id, text=text), message="")
        self.sent.append(SentMessage(chat_id, text, reply_markup))
        return None


@pytest.fixture
def sender() -> FakeSender:
    return FakeSender()


@pytest.fixture
async def scheduler() -> AsyncIterator[AsyncIOScheduler]:
    scheduler = AsyncIOScheduler()
    scheduler.start(paused=True)
    yield scheduler
    scheduler.shutdown(wait=False)


async def test_evening_checkin_lists_habits(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    owner: User,
    sender: FakeSender,
) -> None:
    await add_habit(session, owner, "Read")
    await add_habit(session, owner, "Run")
    await session.commit()

    await send_evening_checkin(sender, session_factory, owner.id)

    [message] = sender.sent
    assert message.chat_id == owner.id
    assert message.text.startswith(texts.EVENING_INTRO)
    assert message.reply_markup is not None
    buttons = [row[0].text for row in message.reply_markup.inline_keyboard]
    assert buttons == ["⬜️ Read", "⬜️ Run"]


@pytest.mark.usefixtures("owner")
async def test_evening_checkin_skipped_without_habits(
    session_factory: async_sessionmaker[AsyncSession], sender: FakeSender
) -> None:
    await send_evening_checkin(sender, session_factory, 123456789)

    assert sender.sent == []


async def test_evening_checkin_skipped_for_unknown_user(
    session_factory: async_sessionmaker[AsyncSession], sender: FakeSender
) -> None:
    await send_evening_checkin(sender, session_factory, 1)

    assert sender.sent == []


async def test_morning_reminder_sent_when_yesterday_is_empty(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    owner: User,
    sender: FakeSender,
) -> None:
    await add_habit(session, owner, "Read")
    await session.commit()

    await send_morning_reminder(sender, session_factory, owner.id)

    [message] = sender.sent
    assert message.text.startswith(texts.MORNING_INTRO)
    assert message.reply_markup is not None
    callback_data = message.reply_markup.inline_keyboard[0][0].callback_data
    yesterday = local_today(owner) - timedelta(days=1)
    assert callback_data is not None
    assert callback_data.endswith(yesterday.isoformat())


async def test_morning_reminder_skipped_when_yesterday_marked(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    owner: User,
    sender: FakeSender,
) -> None:
    habit = await add_habit(session, owner, "Read")
    await toggle_check(session, owner, habit.id, local_today(owner) - timedelta(days=1))
    await session.commit()

    await send_morning_reminder(sender, session_factory, owner.id)

    assert sender.sent == []


async def test_send_failure_is_logged_not_raised(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    owner: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await add_habit(session, owner, "Read")
    await session.commit()

    await send_evening_checkin(FakeSender(fail=True), session_factory, owner.id)

    assert "Failed to send a reminder" in caplog.text


async def test_schedule_creates_jobs_in_user_timezone(
    scheduler: AsyncIOScheduler,
    session_factory: async_sessionmaker[AsyncSession],
    owner: User,
    sender: FakeSender,
) -> None:
    reminders = ReminderScheduler(scheduler, sender, session_factory, time(9, 0))

    reminders.schedule(owner)

    zone = ZoneInfo("Asia/Dubai")
    evening = scheduler.get_job(ReminderScheduler.evening_job_id(owner.id))
    morning = scheduler.get_job(ReminderScheduler.morning_job_id(owner.id))
    assert evening.next_run_time.astimezone(zone).time() == time(23, 0)
    assert morning.next_run_time.astimezone(zone).time() == time(9, 0)


async def test_reschedule_replaces_jobs(
    scheduler: AsyncIOScheduler,
    session_factory: async_sessionmaker[AsyncSession],
    owner: User,
    sender: FakeSender,
) -> None:
    reminders = ReminderScheduler(scheduler, sender, session_factory, time(9, 0))
    reminders.schedule(owner)

    owner.reminder_time = time(21, 30)
    reminders.schedule(owner)

    assert len(scheduler.get_jobs()) == 2
    evening = scheduler.get_job(ReminderScheduler.evening_job_id(owner.id))
    assert evening.next_run_time.astimezone(ZoneInfo("Asia/Dubai")).time() == time(21, 30)
