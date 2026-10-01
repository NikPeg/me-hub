"""Initial schema: users, habits, habit checks.

Revision ID: 0001
Revises:
Create Date: 2026-10-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("reminder_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "habits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("archived_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_habits_name_not_blank")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_habits_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_habits")),
    )
    op.create_index(op.f("ix_habits_user_id"), "habits", ["user_id"], unique=False)
    op.create_index(
        "uq_habits_user_id_name_active",
        "habits",
        ["user_id", "name"],
        unique=True,
        sqlite_where=sa.text("archived_on IS NULL"),
    )
    op.create_table(
        "habit_checks",
        sa.Column("habit_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["habit_id"],
            ["habits.id"],
            name=op.f("fk_habit_checks_habit_id_habits"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("habit_id", "day", name=op.f("pk_habit_checks")),
    )


def downgrade() -> None:
    op.drop_table("habit_checks")
    op.drop_index("uq_habits_user_id_name_active", table_name="habits")
    op.drop_index(op.f("ix_habits_user_id"), table_name="habits")
    op.drop_table("habits")
    op.drop_table("users")
