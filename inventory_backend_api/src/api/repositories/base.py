from __future__ import annotations

from fastapi import Depends, Request

from motor.motor_asyncio import AsyncIOMotorDatabase


# PUBLIC_INTERFACE
def get_db(request: Request) -> AsyncIOMotorDatabase:
    """FastAPI dependency returning MongoDB database from app state."""
    state = getattr(request.app.state, "mongo", None)
    if state is None:
        raise RuntimeError("MongoDB is not initialized")
    return state.db


class BaseRepository:
    """Base repository providing database dependency injection."""

    def __init__(self, db: AsyncIOMotorDatabase = Depends(get_db)):
        self.db = db
