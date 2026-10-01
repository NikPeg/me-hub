from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class HabitHistory:
    """Local-date view of a habit. A habit archived on day X is not tracked from X onwards."""

    started_on: date
    done_days: frozenset[date]
    archived_on: date | None = None

    @property
    def tracked_from(self) -> date:
        return min(self.started_on, *self.done_days) if self.done_days else self.started_on

    def is_tracked_on(self, day: date) -> bool:
        if day < self.tracked_from:
            return False
        return self.archived_on is None or day < self.archived_on

    def last_tracked_day(self, today: date) -> date:
        if self.archived_on is None:
            return today
        return min(today, self.archived_on - ONE_DAY)

    def done_days_until(self, today: date) -> frozenset[date]:
        end = self.last_tracked_day(today)
        return frozenset(day for day in self.done_days if day <= end)


@dataclass(frozen=True, slots=True)
class HabitStats:
    current_streak: int
    longest_streak: int
    total_done: int
    completion_rate: float


def days_between(start: date, end: date) -> Iterator[date]:
    day = start
    while day <= end:
        yield day
        day += ONE_DAY


def current_streak(done_days: frozenset[date], today: date) -> int:
    """Consecutive done days ending today, or yesterday while today is still unmarked."""
    day = today if today in done_days else today - ONE_DAY
    streak = 0
    while day in done_days:
        streak += 1
        day -= ONE_DAY
    return streak


def longest_streak(done_days: Iterable[date]) -> int:
    longest = 0
    run = 0
    previous: date | None = None
    for day in sorted(set(done_days)):
        run = run + 1 if previous is not None and day - previous == ONE_DAY else 1
        longest = max(longest, run)
        previous = day
    return longest


def completion_rate(history: HabitHistory, today: date) -> float:
    start = history.tracked_from
    end = history.last_tracked_day(today)
    if end < start:
        return 0.0
    total_days = (end - start).days + 1
    return len(history.done_days_until(today)) / total_days


def summarize(history: HabitHistory, today: date) -> HabitStats:
    """Stats over the tracked window: days after the archive day or after today are ignored."""
    done_days = history.done_days_until(today)
    is_archived = history.archived_on is not None and history.archived_on <= today
    return HabitStats(
        current_streak=0 if is_archived else current_streak(done_days, today),
        longest_streak=longest_streak(done_days),
        total_done=len(done_days),
        completion_rate=completion_rate(history, today),
    )


def daily_completion(
    histories: Iterable[HabitHistory], start: date, end: date
) -> dict[date, float | None]:
    """Share of tracked habits done per day; None for days without any tracked habit."""
    habits = list(histories)
    result: dict[date, float | None] = {}
    for day in days_between(start, end):
        tracked = [habit for habit in habits if habit.is_tracked_on(day)]
        if not tracked:
            result[day] = None
            continue
        done = sum(1 for habit in tracked if day in habit.done_days)
        result[day] = done / len(tracked)
    return result
