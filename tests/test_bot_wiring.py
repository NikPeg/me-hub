from datetime import date, time
from typing import Any

import pytest
from aiogram.types import Chat, InlineKeyboardMarkup, TelegramObject, Update
from aiogram.types import User as TelegramUser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from me_hub.bot.app import create_dispatcher
from me_hub.bot.config import BotSettings
from me_hub.bot.keyboards import ToggleCheck, checkin_markup, day_picker_markup
from me_hub.bot.middlewares import OwnerOnlyMiddleware
from me_hub.bot.reminders import ReminderScheduler
from me_hub.core.models import Habit

OWNER_ID = 42
DAY = date(2026, 10, 1)


async def handled(_event: TelegramObject, _data: dict[str, Any]) -> str:
    return "handled"


def telegram_user(user_id: int) -> TelegramUser:
    return TelegramUser(id=user_id, is_bot=False, first_name="Test")


@pytest.mark.parametrize(
    ("sender", "chat", "expected"),
    [
        (telegram_user(OWNER_ID), Chat(id=OWNER_ID, type="private"), "handled"),
        (telegram_user(OWNER_ID), None, "handled"),
        (telegram_user(7), Chat(id=7, type="private"), None),
        (telegram_user(OWNER_ID), Chat(id=-100, type="supergroup"), None),
        (None, None, None),
    ],
)
async def test_owner_only_middleware(
    sender: TelegramUser | None, chat: Chat | None, expected: str | None
) -> None:
    middleware = OwnerOnlyMiddleware(OWNER_ID)
    data: dict[str, Any] = {"event_from_user": sender, "event_chat": chat}

    assert await middleware(handled, Update(update_id=1), data) == expected


def test_checkin_markup_marks_done_habits() -> None:
    habits = [
        Habit(id=1, user_id=OWNER_ID, name="Read", started_on=DAY),
        Habit(id=2, user_id=OWNER_ID, name="Run", started_on=DAY),
    ]

    markup = checkin_markup(habits, {2}, DAY)

    buttons = [row[0] for row in markup.inline_keyboard]
    assert [button.text for button in buttons] == ["⬜️ Read", "✅ Run"]
    assert buttons[1].callback_data is not None
    assert ToggleCheck.unpack(buttons[1].callback_data) == ToggleCheck(
        habit_id=2, day=DAY.isoformat()
    )


def test_day_picker_offers_last_week() -> None:
    markup = day_picker_markup(DAY)

    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels[:2] == ["Сегодня", "Вчера"]
    assert len(labels) == 7


async def test_dispatcher_handles_messages_and_callbacks(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    settings = BotSettings(telegram_bot_token=SecretStr("1:token"), telegram_owner_id=OWNER_ID)
    reminders = ReminderScheduler(AsyncIOScheduler(), _NoopSender(), session_factory, time(9))

    dispatcher = create_dispatcher(settings, session_factory, reminders)

    assert {"message", "callback_query"} <= set(dispatcher.resolve_used_update_types())


class _NoopSender:
    async def send_message(
        self, chat_id: int | str, text: str, *, reply_markup: InlineKeyboardMarkup | None = None
    ) -> object:
        return None
