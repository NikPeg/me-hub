from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.core.habits import add_habit, archive_habit, local_today, toggle_check
from me_hub.core.models import User
from me_hub.web.dashboard import GRID_WEEKS, DayState, build_dashboard, grid_start


async def test_empty_dashboard_has_untracked_overall_grid(
    session: AsyncSession, owner: User
) -> None:
    dashboard = await build_dashboard(session, owner)

    assert dashboard.habits == []
    assert dashboard.overall
    assert all(value is None for value in dashboard.overall)


async def test_grids_span_whole_weeks_up_to_today(session: AsyncSession, owner: User) -> None:
    dashboard = await build_dashboard(session, owner)

    today = local_today(owner)
    assert dashboard.today == today
    assert dashboard.start.weekday() == 0
    assert dashboard.start == grid_start(today)
    assert len(dashboard.overall) == (today - dashboard.start).days + 1
    assert GRID_WEEKS * 7 - 6 <= len(dashboard.overall) <= GRID_WEEKS * 7


async def test_habit_grid_marks_done_missed_and_untracked_days(
    session: AsyncSession, owner: User
) -> None:
    habit = await add_habit(session, owner, "Run")
    today = local_today(owner)
    await toggle_check(session, owner, habit.id, today)
    await toggle_check(session, owner, habit.id, today - timedelta(days=2))
    await session.commit()

    dashboard = await build_dashboard(session, owner)

    [grid] = dashboard.habits
    assert grid.name == "Run"
    assert grid.days[-1] == DayState.DONE
    assert grid.days[-2] == DayState.MISSED
    assert grid.days[-3] == DayState.DONE
    assert grid.days[0] == DayState.UNTRACKED
    assert (grid.current_streak, grid.total_done) == (1, 2)
    assert len(grid.days) == len(dashboard.overall)


async def test_overall_grid_is_share_of_done_habits(session: AsyncSession, owner: User) -> None:
    first = await add_habit(session, owner, "Run")
    await add_habit(session, owner, "Read")
    await toggle_check(session, owner, first.id, local_today(owner))
    await session.commit()

    dashboard = await build_dashboard(session, owner)

    assert dashboard.overall[-1] == 0.5


async def test_archived_habits_are_left_out(session: AsyncSession, owner: User) -> None:
    habit = await add_habit(session, owner, "Run")
    await archive_habit(session, owner, habit.id)
    await session.commit()

    assert (await build_dashboard(session, owner)).habits == []
