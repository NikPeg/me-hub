from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.core.colors import HABIT_COLORS
from me_hub.core.habits import (
    MAX_BACKFILL_DAYS,
    DayNotMarkableError,
    DuplicateHabitError,
    HabitNotFoundError,
    active_habits,
    add_habit,
    archive_habit,
    change_habit_color,
    done_habit_ids,
    ensure_markable,
    ensure_user,
    has_checks_on,
    local_today,
    rename_habit,
    toggle_check,
    update_timezone,
)
from me_hub.core.models import User

TODAY = date(2026, 10, 1)


def test_local_today_uses_user_timezone() -> None:
    user = User(id=1, timezone="Asia/Dubai", reminder_time=time(23))
    late_utc_evening = datetime(2026, 9, 30, 21, 30, tzinfo=UTC)
    assert local_today(user, late_utc_evening) == TODAY


@pytest.mark.parametrize("offset", [0, 1, MAX_BACKFILL_DAYS])
def test_recent_days_are_markable(offset: int) -> None:
    ensure_markable(TODAY - timedelta(days=offset), TODAY)


@pytest.mark.parametrize("offset", [-1, MAX_BACKFILL_DAYS + 1])
def test_future_and_old_days_are_not_markable(offset: int) -> None:
    with pytest.raises(DayNotMarkableError):
        ensure_markable(TODAY - timedelta(days=offset), TODAY)


async def test_ensure_user_creates_once(session: AsyncSession) -> None:
    created = await ensure_user(session, 42, "Asia/Dubai", time(23))
    again = await ensure_user(session, 42, "Europe/London", time(21))

    assert again is created
    assert again.timezone == "Asia/Dubai"


async def test_add_habit_appends_and_starts_today(session: AsyncSession, owner: User) -> None:
    first = await add_habit(session, owner, "  Read ")
    second = await add_habit(session, owner, "Run")

    assert [habit.name for habit in await active_habits(session, owner.id)] == ["Read", "Run"]
    assert second.position > first.position
    assert first.started_on == local_today(owner)
    assert first.color in HABIT_COLORS
    assert second.color in HABIT_COLORS
    assert second.color != first.color


async def test_change_habit_color_persists_a_different_color(
    session: AsyncSession, owner: User
) -> None:
    habit = await add_habit(session, owner, "Read")
    original_color = habit.color
    owner_id = owner.id

    changed = await change_habit_color(session, owner_id, habit.id)
    new_color = changed.color
    await session.commit()
    session.expire_all()

    assert new_color != original_color
    assert (await active_habits(session, owner_id))[0].color == new_color


async def test_add_habit_rejects_case_insensitive_duplicate(
    session: AsyncSession, owner: User
) -> None:
    await add_habit(session, owner, "Read")

    with pytest.raises(DuplicateHabitError) as error:
        await add_habit(session, owner, "READ")
    assert error.value.name == "Read"


async def test_add_habit_rejects_blank_name(session: AsyncSession, owner: User) -> None:
    with pytest.raises(ValueError, match="blank"):
        await add_habit(session, owner, "   ")


async def test_rename_habit(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Read")

    renamed = await rename_habit(session, owner.id, habit.id, "read")

    assert renamed.name == "read"


async def test_rename_habit_rejects_taken_name(session: AsyncSession, owner: User) -> None:
    await add_habit(session, owner, "Read")
    run = await add_habit(session, owner, "Run")

    with pytest.raises(DuplicateHabitError):
        await rename_habit(session, owner.id, run.id, "read")


async def test_archive_hides_habit_and_frees_name(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Read")

    archived = await archive_habit(session, owner, habit.id)
    await add_habit(session, owner, "Read")

    assert archived.archived_on == local_today(owner)
    assert habit.id not in {h.id for h in await active_habits(session, owner.id)}
    with pytest.raises(HabitNotFoundError):
        await archive_habit(session, owner, habit.id)


async def test_toggle_check_flips_state(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Read")
    today = local_today(owner)

    assert await toggle_check(session, owner, habit.id, today) is True
    assert await done_habit_ids(session, owner.id, today) == {habit.id}
    assert await has_checks_on(session, owner.id, today)

    assert await toggle_check(session, owner, habit.id, today) is False
    assert await done_habit_ids(session, owner.id, today) == set()
    assert not await has_checks_on(session, owner.id, today)


async def test_toggle_check_allows_backfill(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Read")
    last_week = local_today(owner) - timedelta(days=7)

    assert await toggle_check(session, owner, habit.id, last_week) is True
    assert await has_checks_on(session, owner.id, last_week)


async def test_toggle_check_rejects_future_day(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Read")

    with pytest.raises(DayNotMarkableError):
        await toggle_check(session, owner, habit.id, local_today(owner) + timedelta(days=1))


async def test_toggle_check_rejects_archived_habit(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Read")
    await archive_habit(session, owner, habit.id)

    with pytest.raises(HabitNotFoundError):
        await toggle_check(session, owner, habit.id, local_today(owner))


async def test_toggle_check_rejects_foreign_habit(session: AsyncSession, owner: User) -> None:
    stranger = await ensure_user(session, 7, "UTC", time(21))
    habit = await add_habit(session, stranger, "Secret")

    with pytest.raises(HabitNotFoundError):
        await toggle_check(session, owner, habit.id, local_today(owner))


async def test_update_timezone_validates(session: AsyncSession, owner: User) -> None:
    await update_timezone(session, owner, "Europe/London")
    assert owner.timezone == "Europe/London"

    with pytest.raises(ValueError, match="Unknown timezone"):
        await update_timezone(session, owner, "../../etc/passwd")
