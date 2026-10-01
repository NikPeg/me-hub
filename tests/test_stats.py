from datetime import date, timedelta

import pytest

from me_hub.core.stats import (
    HabitHistory,
    HabitStats,
    completion_rate,
    current_streak,
    daily_completion,
    longest_streak,
    summarize,
)

TODAY = date(2026, 10, 10)


def days_ago(*offsets: int) -> frozenset[date]:
    return frozenset(TODAY - timedelta(days=offset) for offset in offsets)


class TestCurrentStreak:
    def test_empty(self) -> None:
        assert current_streak(frozenset(), TODAY) == 0

    def test_counts_back_from_today(self) -> None:
        assert current_streak(days_ago(0, 1, 2, 4), TODAY) == 3

    def test_unmarked_today_keeps_yesterdays_streak(self) -> None:
        assert current_streak(days_ago(1, 2), TODAY) == 2

    def test_gap_before_yesterday_breaks_streak(self) -> None:
        assert current_streak(days_ago(2, 3), TODAY) == 0

    def test_future_days_are_ignored(self) -> None:
        assert current_streak(days_ago(-1, 0), TODAY) == 1


class TestLongestStreak:
    def test_empty(self) -> None:
        assert longest_streak([]) == 0

    def test_picks_longest_run(self) -> None:
        assert longest_streak(days_ago(0, 1, 5, 6, 7, 9)) == 3

    def test_handles_unsorted_duplicates(self) -> None:
        assert longest_streak([TODAY, TODAY - timedelta(days=1), TODAY]) == 2

    def test_crosses_month_and_year_boundaries(self) -> None:
        assert longest_streak([date(2025, 12, 31), date(2026, 1, 1), date(2026, 1, 2)]) == 3


class TestHabitHistory:
    def test_backfilled_days_extend_tracking_start(self) -> None:
        history = HabitHistory(started_on=TODAY, done_days=days_ago(3))
        assert history.tracked_from == TODAY - timedelta(days=3)

    def test_archive_day_is_not_tracked(self) -> None:
        history = HabitHistory(
            started_on=TODAY - timedelta(days=5),
            done_days=frozenset(),
            archived_on=TODAY - timedelta(days=1),
        )
        assert history.is_tracked_on(TODAY - timedelta(days=2))
        assert not history.is_tracked_on(TODAY - timedelta(days=1))
        assert not history.is_tracked_on(TODAY - timedelta(days=6))


class TestCompletionRate:
    def test_counts_today_as_tracked(self) -> None:
        history = HabitHistory(started_on=TODAY - timedelta(days=3), done_days=days_ago(0, 2))
        assert completion_rate(history, TODAY) == pytest.approx(0.5)

    def test_habit_started_in_future_is_zero(self) -> None:
        history = HabitHistory(started_on=TODAY + timedelta(days=1), done_days=frozenset())
        assert completion_rate(history, TODAY) == 0.0

    def test_stops_at_archive_day(self) -> None:
        history = HabitHistory(
            started_on=TODAY - timedelta(days=9),
            done_days=days_ago(9, 8, 7, 6, 4),
            archived_on=TODAY - timedelta(days=4),
        )
        assert completion_rate(history, TODAY) == pytest.approx(4 / 5)

    def test_archived_on_start_day_is_zero(self) -> None:
        history = HabitHistory(started_on=TODAY, done_days=frozenset(), archived_on=TODAY)
        assert completion_rate(history, TODAY) == 0.0


class TestSummarize:
    def test_active_habit(self) -> None:
        history = HabitHistory(started_on=TODAY - timedelta(days=4), done_days=days_ago(0, 1, 3))
        assert summarize(history, TODAY) == HabitStats(
            current_streak=2, longest_streak=2, total_done=3, completion_rate=3 / 5
        )

    def test_ignores_days_outside_tracked_window(self) -> None:
        history = HabitHistory(
            started_on=TODAY - timedelta(days=4),
            done_days=days_ago(-2, -1, 2, 3),
            archived_on=TODAY - timedelta(days=1),
        )
        stats = summarize(history, TODAY)
        assert stats.total_done == 2
        assert stats.longest_streak == 2
        assert stats.completion_rate == pytest.approx(2 / 3)

    def test_archived_habit_has_no_current_streak(self) -> None:
        history = HabitHistory(
            started_on=TODAY - timedelta(days=4), done_days=days_ago(1, 2), archived_on=TODAY
        )
        stats = summarize(history, TODAY)
        assert stats.current_streak == 0
        assert stats.longest_streak == 2


class TestDailyCompletion:
    def test_ratio_of_tracked_habits(self) -> None:
        start = TODAY - timedelta(days=2)
        read = HabitHistory(started_on=start, done_days=days_ago(0, 1, 2))
        run = HabitHistory(started_on=start, done_days=days_ago(1))
        sleep = HabitHistory(started_on=TODAY - timedelta(days=1), done_days=frozenset())

        assert daily_completion([read, run, sleep], start, TODAY) == {
            TODAY - timedelta(days=2): pytest.approx(1 / 2),
            TODAY - timedelta(days=1): pytest.approx(2 / 3),
            TODAY: pytest.approx(1 / 3),
        }

    def test_days_without_tracked_habits_are_none(self) -> None:
        habit = HabitHistory(started_on=TODAY, done_days=days_ago(0))
        assert daily_completion([habit], TODAY - timedelta(days=1), TODAY) == {
            TODAY - timedelta(days=1): None,
            TODAY: 1.0,
        }

    def test_archived_habit_excluded_from_archive_day(self) -> None:
        start = TODAY - timedelta(days=1)
        kept = HabitHistory(started_on=start, done_days=days_ago(0, 1))
        dropped = HabitHistory(started_on=start, done_days=frozenset(), archived_on=TODAY)
        assert daily_completion([kept, dropped], start, TODAY) == {
            start: pytest.approx(1 / 2),
            TODAY: 1.0,
        }

    def test_empty_range(self) -> None:
        assert daily_completion([], TODAY, TODAY - timedelta(days=1)) == {}
