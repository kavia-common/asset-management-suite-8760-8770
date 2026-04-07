from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


# PUBLIC_INTERFACE
def get_session(request: Request) -> AsyncSession:
    """FastAPI dependency returning a PostgreSQL AsyncSession from app state."""
    state = getattr(request.app.state, "postgres", None)
    if state is None:
        raise RuntimeError("PostgreSQL is not initialized")

    # Session is request-scoped by creating a new one each time; SQLAlchemy manages pooling on engine.
    return state.sessionmaker()


class BaseRepository:
    """Base repository providing DB session dependency injection."""

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
