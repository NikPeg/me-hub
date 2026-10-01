from datetime import date

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.bot import texts
from me_hub.bot.formatting import parse_day
from me_hub.bot.keyboards import PickDay, ToggleCheck, day_picker_markup
from me_hub.bot.messaging import show_in_place
from me_hub.bot.views import NO_HABITS_VIEW, checkin_view
from me_hub.core.habits import (
    DayNotMarkableError,
    HabitNotFoundError,
    ensure_markable,
    local_today,
    toggle_check,
)
from me_hub.core.models import User

router = Router(name="checkin")


async def answer_checkin(message: Message, session: AsyncSession, user: User, day: date) -> None:
    view = await checkin_view(session, user, day) or NO_HABITS_VIEW
    await message.answer(view.text, reply_markup=view.markup)


@router.message(Command("today"))
async def today(message: Message, session: AsyncSession, user: User) -> None:
    await answer_checkin(message, session, user, local_today(user))


@router.message(Command("mark"))
async def mark(message: Message, command: CommandObject, session: AsyncSession, user: User) -> None:
    current_day = local_today(user)
    if not command.args:
        await message.answer(texts.PICK_DAY, reply_markup=day_picker_markup(current_day))
        return
    try:
        day = parse_day(command.args, current_day)
        ensure_markable(day, current_day)
    except DayNotMarkableError:
        await message.answer(texts.DAY_NOT_MARKABLE)
        return
    except ValueError:
        await message.answer(texts.BAD_DATE)
        return
    await answer_checkin(message, session, user, day)


async def _callback_day(callback: CallbackQuery, raw_day: str, user: User) -> date | None:
    try:
        day = date.fromisoformat(raw_day)
        ensure_markable(day, local_today(user))
    except DayNotMarkableError:
        await callback.answer(texts.DAY_NOT_MARKABLE, show_alert=True)
        return None
    except ValueError:
        await callback.answer(texts.BAD_DATE, show_alert=True)
        return None
    return day


@router.callback_query(PickDay.filter())
async def pick_day(
    callback: CallbackQuery, callback_data: PickDay, session: AsyncSession, user: User
) -> None:
    day = await _callback_day(callback, callback_data.day, user)
    if day is None:
        return
    await show_in_place(callback, await checkin_view(session, user, day) or NO_HABITS_VIEW)
    await callback.answer()


@router.callback_query(ToggleCheck.filter())
async def toggle(
    callback: CallbackQuery, callback_data: ToggleCheck, session: AsyncSession, user: User
) -> None:
    day = await _callback_day(callback, callback_data.day, user)
    if day is None:
        return
    try:
        await toggle_check(session, user, callback_data.habit_id, day)
    except HabitNotFoundError:
        await callback.answer(texts.HABIT_NOT_FOUND, show_alert=True)
    else:
        await session.commit()
        await callback.answer()
    await show_in_place(callback, await checkin_view(session, user, day) or NO_HABITS_VIEW)
