"""SQLAlchemy async engine and session management.

Provides the database engine factory and session context manager for
the flight data persistence layer. Uses ``aiosqlite`` as the async
SQLite backend with WAL mode for safe concurrent access.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from singularity.persistence.models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


# ---------------------------------------------------------------------------
# Engine lifecycle
# ---------------------------------------------------------------------------

async def init_database(
    db_path: str | Path = "singularity_cc.db",
    echo: bool = False,
) -> AsyncEngine:
    """Initialize the async SQLAlchemy engine and create all tables.

    Configures the SQLite connection with WAL mode for concurrent
    read/write safety. Creates all ORM tables if they do not exist.

    Args:
        db_path: Path to the SQLite database file. Defaults to
            ``"singularity_cc.db"`` in the current directory.
        echo: If ``True``, emit SQL statements to the logger.

    Returns:
        The initialized :class:`AsyncEngine`.
    """
    global _engine, _session_factory

    db_url = f"sqlite+aiosqlite:///{db_path}"
    _engine = create_async_engine(db_url, echo=echo)

    # Enable WAL mode on every raw connection for concurrent access
    @event.listens_for(_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn: object, _: object) -> None:
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized at %s (WAL mode)", db_path)
    return _engine


async def close_database() -> None:
    """Dispose of the engine and release all connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")
        _engine = None
        _session_factory = None


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session with automatic commit/rollback.

    Usage::

        async with get_session() as session:
            session.add(some_model)
            # auto-committed on exit, rolled back on exception

    Yields:
        An :class:`AsyncSession` bound to the current engine.

    Raises:
        RuntimeError: If :func:`init_database` has not been called.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_engine() -> AsyncEngine:
    """Return the current engine instance.

    Raises:
        RuntimeError: If :func:`init_database` has not been called.
    """
    if _engine is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _engine
