from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

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
