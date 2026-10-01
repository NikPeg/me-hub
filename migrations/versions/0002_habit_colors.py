"""Assign a persistent display color to each habit.

Revision ID: 0002
Revises: 0001
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLORS = (
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


def upgrade() -> None:
    op.add_column("habits", sa.Column("color", sa.String(length=7), nullable=True))
    connection = op.get_bind()
    used_by_user: dict[int, set[str]] = {}
    rows = connection.execute(sa.text("SELECT id, user_id FROM habits ORDER BY user_id, id"))
    for habit_id, user_id in rows:
        used = used_by_user.setdefault(user_id, set())
        available = [color for color in COLORS if color not in used]
        color = secrets.choice(available or COLORS)
        used.add(color)
        connection.execute(
            sa.text("UPDATE habits SET color = :color WHERE id = :id"),
            {"color": color, "id": habit_id},
        )
    with op.batch_alter_table("habits") as batch_op:
        batch_op.alter_column("color", existing_type=sa.String(length=7), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("habits") as batch_op:
        batch_op.drop_column("color")
