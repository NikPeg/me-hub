import re
from datetime import date, time, timedelta

from me_hub.bot import texts

_TIME_PATTERN = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")
_DAY_MONTH_PATTERN = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$")


def format_day(day: date, today: date) -> str:
    label = f"{day.day} {texts.MONTHS_GENITIVE[day.month - 1]}"
    if day.year != today.year:
        label = f"{label} {day.year}"
    if day == today:
        return texts.TODAY_LABEL.format(label=label)
    if day == today - timedelta(days=1):
        return texts.YESTERDAY_LABEL.format(label=label)
    return label


def format_day_button(day: date, today: date) -> str:
    if day == today:
        return texts.TODAY_BUTTON
    if day == today - timedelta(days=1):
        return texts.YESTERDAY_BUTTON
    return f"{texts.WEEKDAYS_SHORT[day.weekday()]}, {day:%d.%m}"


def format_time(value: time) -> str:
    return f"{value:%H:%M}"


def parse_time(text: str) -> time:
    match = _TIME_PATTERN.match(text.strip())
    if match is None:
        raise ValueError(f"Invalid time: {text!r}")
    return time(int(match.group(1)), int(match.group(2)))


def parse_day(text: str, today: date) -> date:
    """Parses YYYY-MM-DD, DD.MM.YYYY or DD.MM (the most recent such day not after today)."""
    value = text.strip()
    match = _DAY_MONTH_PATTERN.match(value)
    if match is None:
        return date.fromisoformat(value)
    day, month, year = int(match.group(1)), int(match.group(2)), match.group(3)
    if year is not None:
        return date(int(year), month, day)
    candidate = date(today.year, month, day)
    return candidate if candidate <= today else date(today.year - 1, month, day)
