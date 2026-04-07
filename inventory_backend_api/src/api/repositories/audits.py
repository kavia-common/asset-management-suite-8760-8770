from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING

from src.api.core.serialization import now_utc
from src.api.repositories.base import BaseRepository


class AuditsRepository(BaseRepository):
    """MongoDB operations for audit logs."""

    @property
    def col(self):
        return self.db["audits"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("created_at", DESCENDING)])
        await self.col.create_index([("entity_type", DESCENDING), ("entity_id", DESCENDING)])

    async def create(
        self,
        *,
        actor_user_id: ObjectId | None,
        action: str,
        entity_type: str,
        entity_id: ObjectId | None,
        detail: dict[str, Any],
    ) -> None:
        await self.col.insert_one(
            {
                "actor_user_id": actor_user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "detail": detail,
                "created_at": now_utc(),
            }
        )

    async def list(self, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        cur = self.col.find({}).sort("created_at", DESCENDING).skip(offset).limit(limit)
        return [doc async for doc in cur]
