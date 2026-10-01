from pathlib import Path
from typing import cast

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from me_hub.core.colors import HABIT_COLORS
from me_hub.core.models import Base


def sync_url(database_path: Path) -> str:
    return f"sqlite:///{database_path}"


def test_migrations_match_models(migrated_database_url: str, database_path: Path) -> None:
    engine = create_engine(sync_url(database_path))
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()


def test_downgrade_removes_all_tables(
    migrated_database_url: str, alembic_config: Config, database_path: Path
) -> None:
    command.downgrade(alembic_config, "base")

    engine = create_engine(sync_url(database_path))
    try:
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_creates_missing_database_directory(
    alembic_config: Config, database_path: Path
) -> None:
    assert not database_path.parent.exists()

    command.upgrade(alembic_config, "head")

    assert database_path.exists()


def test_upgrade_assigns_colors_to_existing_habits(
    alembic_config: Config, database_path: Path
) -> None:
    command.upgrade(alembic_config, "0001")
    engine = create_engine(sync_url(database_path))
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, timezone, reminder_time, created_at) "
                    "VALUES (1, 'UTC', '23:00:00', '2026-10-01 00:00:00')"
                )
            )
            for habit_id, name in ((1, "Read"), (2, "Run")):
                connection.execute(
                    text(
                        "INSERT INTO habits "
                        "(id, user_id, name, position, started_on, created_at) "
                        "VALUES (:id, 1, :name, :id, '2026-10-01', '2026-10-01 00:00:00')"
                    ),
                    {"id": habit_id, "name": name},
                )
    finally:
        engine.dispose()

    command.upgrade(alembic_config, "head")
    engine = create_engine(sync_url(database_path))
    try:
        with engine.connect() as connection:
            colors = cast(
                list[str],
                connection.execute(text("SELECT color FROM habits ORDER BY id")).scalars().all(),
            )
            assert len(set(colors)) == 2
            assert set(colors) <= set(HABIT_COLORS)
    finally:
        engine.dispose()
