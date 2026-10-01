from collections.abc import Sequence
from datetime import date, timedelta
from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from me_hub.bot import texts
from me_hub.bot.formatting import format_day_button
from me_hub.core.models import Habit

DAY_PICKER_DAYS = 7


class ToggleCheck(CallbackData, prefix="chk"):
    habit_id: int
    day: str


class PickDay(CallbackData, prefix="day"):
    day: str


class HabitActionKind(StrEnum):
    RENAME = "rename"
    COLOR = "color"
    ARCHIVE = "archive"
    CONFIRM_ARCHIVE = "confirm"
    BACK = "back"


class HabitAction(CallbackData, prefix="hab"):
    action: HabitActionKind
    habit_id: int


def checkin_markup(habits: Sequence[Habit], done_ids: set[int], day: date) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for habit in habits:
        mark = "✅" if habit.id in done_ids else "⬜️"
        builder.button(
            text=f"{mark} {habit.name}",
            callback_data=ToggleCheck(habit_id=habit.id, day=day.isoformat()),
        )
    builder.adjust(1)
    return builder.as_markup()


def day_picker_markup(today: date) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for offset in range(DAY_PICKER_DAYS):
        day = today - timedelta(days=offset)
        builder.button(
            text=format_day_button(day, today), callback_data=PickDay(day=day.isoformat())
        )
    builder.adjust(2, 3)
    return builder.as_markup()


def habits_markup(habits: Sequence[Habit]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for habit in habits:
        builder.button(
            text=f"✏️ {habit.name}",
            callback_data=HabitAction(action=HabitActionKind.RENAME, habit_id=habit.id),
        )
        builder.button(
            text=texts.CHANGE_COLOR_BUTTON,
            callback_data=HabitAction(action=HabitActionKind.COLOR, habit_id=habit.id),
        )
        builder.button(
            text="🗄",
            callback_data=HabitAction(action=HabitActionKind.ARCHIVE, habit_id=habit.id),
        )
    builder.adjust(3)
    return builder.as_markup()


def confirm_archive_markup(habit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.ARCHIVE_BUTTON,
        callback_data=HabitAction(action=HabitActionKind.CONFIRM_ARCHIVE, habit_id=habit_id),
    )
    builder.button(
        text=texts.BACK_BUTTON,
        callback_data=HabitAction(action=HabitActionKind.BACK, habit_id=habit_id),
    )
    builder.adjust(2)
    return builder.as_markup()
