from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.core.config import get_settings


@dataclass
class PostgresState:
    """Holds PostgreSQL async engine/sessionmaker for the app lifespan."""

    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]


def _build_postgres_dsn() -> str:
    """Build async SQLAlchemy DSN from Settings."""
    settings = get_settings()
    if (
        not settings.postgres_host
        or not settings.postgres_db
        or not settings.postgres_user
        or settings.postgres_password == ""
    ):
        raise RuntimeError(
            "PostgreSQL is not configured. Please set POSTGRES_HOST, POSTGRES_PORT, "
            "POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD environment variables."
        )

    # asyncpg DSN for SQLAlchemy
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


# PUBLIC_INTERFACE
async def connect_to_postgres() -> PostgresState:
    """Create PostgreSQL engine and sessionmaker using environment variables.

    Requires:
    - POSTGRES_HOST
    - POSTGRES_PORT
    - POSTGRES_DB
    - POSTGRES_USER
    - POSTGRES_PASSWORD
    """
    dsn = _build_postgres_dsn()
    engine = create_async_engine(dsn, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresState(engine=engine, sessionmaker=sessionmaker)


# PUBLIC_INTERFACE
async def close_postgres(state: PostgresState) -> None:
    """Dispose SQLAlchemy engine."""
    await state.engine.dispose()
