from __future__ import annotations

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.api.core.config import get_settings


@dataclass
class MongoState:
    """Holds MongoDB client and database references for the app lifespan."""

    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase


# PUBLIC_INTERFACE
async def connect_to_mongo() -> MongoState:
    """Create MongoDB client/database using environment variables.

    Requires:
    - MONGODB_URL
    - MONGODB_DB
    """
    settings = get_settings()
    if not settings.mongodb_url or not settings.mongodb_db:
        raise RuntimeError(
            "MongoDB is not configured. Please set MONGODB_URL and MONGODB_DB environment variables."
        )

    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db]
    return MongoState(client=client, db=db)


# PUBLIC_INTERFACE
async def close_mongo(state: MongoState) -> None:
    """Close MongoDB client."""
    state.client.close()
