from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import ASCENDING

from src.api.core.serialization import now_utc
from src.api.repositories.base import BaseRepository


class AssetsRepository(BaseRepository):
    """MongoDB operations for assets/devices."""

    @property
    def col(self):
        return self.db["assets"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("asset_tag", ASCENDING)], unique=True)

    async def get_by_id(self, asset_id: ObjectId) -> dict[str, Any] | None:
        return await self.col.find_one({"_id": asset_id})

    async def get_by_asset_tag(self, asset_tag: str) -> dict[str, Any] | None:
        return await self.col.find_one({"asset_tag": asset_tag})

    async def list(self, q: str | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if q:
            query = {"$or": [{"asset_tag": {"$regex": q, "$options": "i"}}, {"serial_number": {"$regex": q, "$options": "i"}}]}
        cur = self.col.find(query).sort("created_at", ASCENDING).skip(offset).limit(limit)
        return [doc async for doc in cur]

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        now = now_utc()
        doc = {
            **doc,
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        res = await self.col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def update(self, asset_id: ObjectId, updates: dict[str, Any]) -> dict[str, Any] | None:
        updates["updated_at"] = now_utc()
        await self.col.update_one({"_id": asset_id}, {"$set": updates})
        return await self.get_by_id(asset_id)
