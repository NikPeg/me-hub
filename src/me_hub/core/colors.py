import secrets
from collections.abc import Iterable

HABIT_COLORS = (
    "#e11d48",
    "#f97316",
    "#ca8a04",
    "#16a34a",
    "#0d9488",
    "#7c3aed",
    "#c026d3",
    "#db2777",
    "#b45309",
    "#4f46e5",
)


def random_habit_color(used: Iterable[str] = (), current: str | None = None) -> str:
    unavailable = set(used)
    if current is not None:
        unavailable.add(current)
    available = [color for color in HABIT_COLORS if color not in unavailable]
    if not available:
        available = [color for color in HABIT_COLORS if color != current]
    return secrets.choice(available)


def default_habit_color() -> str:
    return random_habit_color()
