from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.bot import texts
from me_hub.bot.config import BotSettings
from me_hub.bot.formatting import format_time, parse_time
from me_hub.bot.reminders import ReminderScheduler
from me_hub.core.habits import update_reminder_time, update_timezone
from me_hub.core.models import User, validate_timezone

router = Router(name="settings")


@router.message(Command("settings"))
async def show_settings(message: Message, user: User, config: BotSettings) -> None:
    await message.answer(
        texts.SETTINGS.format(
            timezone=escape(user.timezone),
            reminder_time=format_time(user.reminder_time),
            morning_time=format_time(config.morning_reminder_time),
        )
    )


@router.message(Command("timezone"))
async def change_timezone(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
    reminders: ReminderScheduler,
) -> None:
    if not command.args:
        await message.answer(texts.TIMEZONE_USAGE)
        return
    try:
        timezone = validate_timezone(command.args.strip())
    except ValueError:
        await message.answer(texts.UNKNOWN_TIMEZONE)
        return
    await update_timezone(session, user, timezone)
    await session.commit()
    reminders.schedule(user)
    await message.answer(
        texts.TIMEZONE_UPDATED.format(
            timezone=escape(user.timezone), reminder_time=format_time(user.reminder_time)
        )
    )


@router.message(Command("reminder"))
async def change_reminder_time(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
    reminders: ReminderScheduler,
) -> None:
    try:
        reminder_time = parse_time(command.args or "")
    except ValueError:
        await message.answer(texts.REMINDER_USAGE)
        return
    await update_reminder_time(session, user, reminder_time)
    await session.commit()
    reminders.schedule(user)
    await message.answer(
        texts.REMINDER_UPDATED.format(
            reminder_time=format_time(user.reminder_time), timezone=escape(user.timezone)
        )
    )
