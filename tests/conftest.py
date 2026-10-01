from collections.abc import AsyncIterator
from datetime import time
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from me_hub.core.db import create_engine, create_session_factory
from me_hub.core.models import User

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "me_hub.db"


@pytest.fixture
def database_url(database_path: Path) -> str:
    return f"sqlite+aiosqlite:///{database_path}"


@pytest.fixture
def alembic_config(database_url: str) -> Config:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.attributes["database_url"] = database_url
    config.attributes["configure_logging"] = False
    return config


@pytest.fixture
def migrated_database_url(alembic_config: Config, database_url: str) -> str:
    command.upgrade(alembic_config, "head")
    return database_url


@pytest.fixture
async def session_factory(
    migrated_database_url: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def owner(session: AsyncSession) -> User:
    user = User(id=123456789, timezone="Asia/Dubai", reminder_time=time(23, 0))
    session.add(user)
    await session.commit()
    return user
