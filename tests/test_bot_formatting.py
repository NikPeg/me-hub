from datetime import date, time

import pytest

from me_hub.bot.formatting import format_day, format_day_button, parse_day, parse_time

TODAY = date(2026, 10, 1)


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 1), "сегодня, 1 октября"),
        (date(2026, 9, 30), "вчера, 30 сентября"),
        (date(2026, 9, 28), "28 сентября"),
        (date(2025, 12, 31), "31 декабря 2025"),
    ],
)
def test_format_day(day: date, expected: str) -> None:
    assert format_day(day, TODAY) == expected


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 1), "Сегодня"),
        (date(2026, 9, 30), "Вчера"),
        (date(2026, 9, 28), "пн, 28.09"),
    ],
)
def test_format_day_button(day: date, expected: str) -> None:
    assert format_day_button(day, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("23:00", time(23, 0)), ("9:05", time(9, 5)), (" 07.30 ", time(7, 30))],
)
def test_parse_time(text: str, expected: time) -> None:
    assert parse_time(text) == expected


@pytest.mark.parametrize("text", ["", "24:00", "12:60", "noon", "12"])
def test_parse_time_rejects_invalid(text: str) -> None:
    with pytest.raises(ValueError, match="Invalid time"):
        parse_time(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-09-28", date(2026, 9, 28)),
        ("28.09.2026", date(2026, 9, 28)),
        ("28.09", date(2026, 9, 28)),
        ("1.10", date(2026, 10, 1)),
        ("15.12", date(2025, 12, 15)),
    ],
)
def test_parse_day(text: str, expected: date) -> None:
    assert parse_day(text, TODAY) == expected


@pytest.mark.parametrize("text", ["", "yesterday", "31.02", "2026-13-01"])
def test_parse_day_rejects_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        parse_day(text, TODAY)
