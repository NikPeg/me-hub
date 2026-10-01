from pathlib import Path
from typing import Any

from sqlalchemy import Connection, event, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

SQLITE_BUSY_TIMEOUT_MS = 5000


def ensure_database_dir(url: str) -> None:
    parsed = make_url(url)
    database = parsed.database
    if parsed.get_backend_name() == "sqlite" and database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_engine(url: str) -> AsyncEngine:
    """Engine for application code. Migrations use their own engine without these pragmas,
    because SQLite batch table rebuilds must run with foreign keys disabled."""
    ensure_database_dir(url)
    engine = create_async_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _configure_sqlite_connection)
        event.listen(engine.sync_engine, "begin", _begin_sqlite_transaction)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _configure_sqlite_connection(dbapi_connection: Any, _connection_record: Any) -> None:
    # Hand transaction control to SQLAlchemy so reads and writes share one transaction;
    # the driver would otherwise only emit BEGIN before DML statements.
    dbapi_connection.isolation_level = None
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def _begin_sqlite_transaction(connection: Connection) -> None:
    connection.exec_driver_sql("BEGIN")
