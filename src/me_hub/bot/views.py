from dataclasses import dataclass
from datetime import date
from html import escape

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.bot import texts
from me_hub.bot.formatting import format_day
from me_hub.bot.keyboards import checkin_markup, habits_markup
from me_hub.core.habits import active_habits, done_habit_ids, local_today
from me_hub.core.models import User


@dataclass(frozen=True, slots=True)
class View:
    text: str
    markup: InlineKeyboardMarkup | None = None


NO_HABITS_VIEW = View(texts.NO_HABITS)


async def checkin_view(
    session: AsyncSession, user: User, day: date, intro: str | None = None
) -> View | None:
    """Check-in message for a day, or None when there are no active habits."""
    habits = await active_habits(session, user.id)
    if not habits:
        return None
    done_ids = await done_habit_ids(session, user.id, day)
    title = texts.CHECKIN_TITLE.format(
        day=escape(format_day(day, local_today(user))),
        done=sum(1 for habit in habits if habit.id in done_ids),
        total=len(habits),
    )
    text = f"{intro}\n\n{title}" if intro else title
    return View(text, checkin_markup(habits, done_ids, day))


async def habits_view(session: AsyncSession, user: User) -> View:
    habits = await active_habits(session, user.id)
    if not habits:
        return NO_HABITS_VIEW
    return View(texts.HABITS_TITLE, habits_markup(habits))
