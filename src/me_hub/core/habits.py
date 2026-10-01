from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.core.models import Habit, HabitCheck, User, normalize_habit_name, utcnow

MAX_BACKFILL_DAYS = 365


class HabitError(Exception):
    """Base class for expected, user-facing habit errors."""


class HabitNotFoundError(HabitError):
    pass


class DuplicateHabitError(HabitError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Habit {name!r} already exists")
        self.name = name


class DayNotMarkableError(HabitError):
    def __init__(self, day: date) -> None:
        super().__init__(f"Day {day.isoformat()} cannot be marked")
        self.day = day


def local_today(user: User, now: datetime | None = None) -> date:
    return (now or utcnow()).astimezone(user.zone).date()


def ensure_markable(day: date, today: date) -> None:
    if day > today or day < today - timedelta(days=MAX_BACKFILL_DAYS):
        raise DayNotMarkableError(day)


async def ensure_user(
    session: AsyncSession, user_id: int, timezone: str, reminder_time: time
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, timezone=timezone, reminder_time=reminder_time)
        session.add(user)
        await session.flush()
    return user


async def active_habits(session: AsyncSession, user_id: int) -> list[Habit]:
    result = await session.scalars(
        select(Habit)
        .where(Habit.user_id == user_id, Habit.archived_on.is_(None))
        .order_by(Habit.position, Habit.id)
    )
    return list(result)


async def get_active_habit(session: AsyncSession, user_id: int, habit_id: int) -> Habit:
    habit = await session.scalar(
        select(Habit).where(
            Habit.id == habit_id, Habit.user_id == user_id, Habit.archived_on.is_(None)
        )
    )
    if habit is None:
        raise HabitNotFoundError(f"Habit {habit_id} not found")
    return habit


async def _ensure_unique_name(
    session: AsyncSession, user_id: int, name: str, exclude_id: int | None = None
) -> None:
    for habit in await active_habits(session, user_id):
        if habit.id != exclude_id and habit.name.casefold() == name.casefold():
            raise DuplicateHabitError(habit.name)


async def add_habit(session: AsyncSession, user: User, name: str) -> Habit:
    name = normalize_habit_name(name)
    await _ensure_unique_name(session, user.id, name)
    last_position = await session.scalar(
        select(func.max(Habit.position)).where(Habit.user_id == user.id)
    )
    habit = Habit(
        user_id=user.id,
        name=name,
        position=(last_position or 0) + 1,
        started_on=local_today(user),
    )
    session.add(habit)
    await session.flush()
    return habit


async def rename_habit(session: AsyncSession, user_id: int, habit_id: int, name: str) -> Habit:
    name = normalize_habit_name(name)
    habit = await get_active_habit(session, user_id, habit_id)
    await _ensure_unique_name(session, user_id, name, exclude_id=habit.id)
    habit.name = name
    await session.flush()
    return habit


async def archive_habit(session: AsyncSession, user: User, habit_id: int) -> Habit:
    habit = await get_active_habit(session, user.id, habit_id)
    habit.archived_on = local_today(user)
    await session.flush()
    return habit


async def done_habit_ids(session: AsyncSession, user_id: int, day: date) -> set[int]:
    result = await session.scalars(
        select(HabitCheck.habit_id)
        .join(Habit, Habit.id == HabitCheck.habit_id)
        .where(Habit.user_id == user_id, HabitCheck.day == day)
    )
    return set(result)


async def has_checks_on(session: AsyncSession, user_id: int, day: date) -> bool:
    query = select(
        exists().where(
            HabitCheck.habit_id == Habit.id, Habit.user_id == user_id, HabitCheck.day == day
        )
    )
    return bool(await session.scalar(query))


async def toggle_check(session: AsyncSession, user: User, habit_id: int, day: date) -> bool:
    """Flips the done state of an active habit on a local day; returns the new state."""
    ensure_markable(day, local_today(user))
    habit = await get_active_habit(session, user.id, habit_id)
    check = await session.get(HabitCheck, (habit.id, day))
    if check is not None:
        await session.delete(check)
        await session.flush()
        return False
    session.add(HabitCheck(habit_id=habit.id, day=day))
    await session.flush()
    return True


async def update_timezone(session: AsyncSession, user: User, timezone: str) -> User:
    user.timezone = timezone
    await session.flush()
    return user


async def update_reminder_time(session: AsyncSession, user: User, reminder_time: time) -> User:
    user.reminder_time = reminder_time
    await session.flush()
    return user


async def done_days_by_habit(
    session: AsyncSession, habit_ids: Iterable[int]
) -> dict[int, frozenset[date]]:
    ids = list(habit_ids)
    days: dict[int, set[date]] = {habit_id: set() for habit_id in ids}
    if ids:
        rows = await session.execute(
            select(HabitCheck.habit_id, HabitCheck.day).where(HabitCheck.habit_id.in_(ids))
        )
        for habit_id, day in rows:
            days[habit_id].add(day)
    return {habit_id: frozenset(done) for habit_id, done in days.items()}
