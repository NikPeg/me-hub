from datetime import date, timedelta
from enum import IntEnum

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.core.habits import active_habits, done_days_by_habit, local_today
from me_hub.core.models import User
from me_hub.core.stats import HabitHistory, daily_completion, days_between, summarize

GRID_WEEKS = 53


class DayState(IntEnum):
    UNTRACKED = 0
    MISSED = 1
    DONE = 2


class HabitGrid(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    color: str
    current_streak: int
    longest_streak: int
    total_done: int
    completion_rate: float
    days: list[DayState]


class Dashboard(BaseModel):
    """Grids cover consecutive days from `start` (a Monday) to `today`, so the client lays
    them out in week columns without any date arithmetic."""

    model_config = ConfigDict(frozen=True)

    start: date
    today: date
    overall: list[float | None]
    habits: list[HabitGrid]


def grid_start(today: date) -> date:
    return today - timedelta(days=today.weekday(), weeks=GRID_WEEKS - 1)


def day_state(history: HabitHistory, day: date) -> DayState:
    if day in history.done_days:
        return DayState.DONE
    return DayState.MISSED if history.is_tracked_on(day) else DayState.UNTRACKED


async def build_dashboard(session: AsyncSession, user: User) -> Dashboard:
    today = local_today(user)
    start = grid_start(today)
    habits = await active_habits(session, user.id)
    done_days = await done_days_by_habit(session, (habit.id for habit in habits))
    histories = {
        habit.id: HabitHistory(started_on=habit.started_on, done_days=done_days[habit.id])
        for habit in habits
    }
    completion = daily_completion(histories.values(), start, today)
    grids = []
    for habit in habits:
        history = histories[habit.id]
        stats = summarize(history, today)
        grids.append(
            HabitGrid(
                id=habit.id,
                name=habit.name,
                color=habit.color,
                current_streak=stats.current_streak,
                longest_streak=stats.longest_streak,
                total_done=stats.total_done,
                completion_rate=stats.completion_rate,
                days=[day_state(history, day) for day in days_between(start, today)],
            )
        )
    return Dashboard(
        start=start, today=today, overall=[completion[day] for day in completion], habits=grids
    )
