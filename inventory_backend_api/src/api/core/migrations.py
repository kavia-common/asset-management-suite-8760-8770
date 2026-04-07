from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.models.db_models import Base


# PUBLIC_INTERFACE
async def run_migrations(engine: AsyncEngine) -> None:
    """Apply database schema migrations.

    For this project we use SQLAlchemy metadata `create_all` as an idempotent
    migration step, which is sufficient for the current schema.

    Parameters:
    - engine: async SQLAlchemy engine

    Returns:
    - None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
