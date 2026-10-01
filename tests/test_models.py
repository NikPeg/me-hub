from datetime import UTC, date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.core.models import Habit, HabitCheck, User

OWNER_ID = 123456789  # matches the `owner` fixture
DUBAI = timezone(timedelta(hours=4))
DAY = date(2026, 10, 1)


def make_habit(name: str = "Read", archived_on: date | None = None) -> Habit:
    return Habit(user_id=OWNER_ID, name=name, started_on=DAY, archived_on=archived_on)


async def test_sqlite_pragmas_are_applied(session: AsyncSession) -> None:
    assert (await session.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1
    assert (await session.execute(text("PRAGMA journal_mode"))).scalar_one() == "wal"


async def test_datetimes_round_trip_as_aware_utc(session: AsyncSession) -> None:
    created_at = datetime(2026, 10, 1, 23, 30, tzinfo=DUBAI)
    session.add(User(id=OWNER_ID, timezone="UTC", reminder_time=time(21), created_at=created_at))
    await session.commit()
    session.expunge_all()

    user = await session.get_one(User, OWNER_ID)

    assert user.created_at == created_at
    assert user.created_at.tzinfo is UTC


async def test_naive_datetime_is_rejected(session: AsyncSession) -> None:
    naive = datetime(2026, 1, 1)  # noqa: DTZ001
    session.add(User(id=OWNER_ID, timezone="UTC", reminder_time=time(21), created_at=naive))

    with pytest.raises(StatementError, match="Naive datetimes"):
        await session.commit()


def test_unknown_timezone_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown timezone"):
        User(id=OWNER_ID, timezone="Mars/Olympus", reminder_time=time(21))


@pytest.mark.parametrize("name", ["", "   ", "\t\n", "x" * 65])
def test_invalid_habit_name_is_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="Habit name"):
        make_habit(name)


def test_habit_name_whitespace_is_normalized() -> None:
    assert make_habit("  Read \n  books ").name == "Read books"


@pytest.mark.usefixtures("owner")
async def test_active_habit_names_are_unique_per_user(session: AsyncSession) -> None:
    session.add_all([make_habit(), make_habit()])

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        await session.commit()


@pytest.mark.usefixtures("owner")
async def test_archived_habit_name_can_be_reused(session: AsyncSession) -> None:
    session.add_all([make_habit(archived_on=DAY), make_habit()])

    await session.commit()

    assert await session.scalar(select(func.count()).select_from(Habit)) == 2


async def test_check_requires_existing_habit(session: AsyncSession) -> None:
    session.add(HabitCheck(habit_id=999, day=DAY))

    with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
        await session.commit()


@pytest.mark.usefixtures("owner")
async def test_same_day_cannot_be_checked_twice(session: AsyncSession) -> None:
    habit = make_habit()
    session.add(habit)
    await session.flush()
    row = {"habit_id": habit.id, "day": DAY, "created_at": datetime.now(UTC)}

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        await session.execute(insert(HabitCheck), [row, row])


@pytest.mark.usefixtures("owner")
async def test_deleting_user_cascades_to_habits_and_checks(session: AsyncSession) -> None:
    habit = make_habit()
    session.add(habit)
    await session.flush()
    session.add(HabitCheck(habit_id=habit.id, day=DAY))
    await session.commit()

    await session.execute(delete(User).where(User.id == OWNER_ID))
    await session.commit()

    assert await session.scalar(select(func.count()).select_from(Habit)) == 0
    assert await session.scalar(select(func.count()).select_from(HabitCheck)) == 0
