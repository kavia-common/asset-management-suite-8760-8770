from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from src.api.core.serialization import now_utc
from src.api.models.schemas import AllocationStatus
from src.api.repositories.base import BaseRepository


class AllocationsRepository(BaseRepository):
    """MongoDB operations for allocations and transfer workflow."""

    @property
    def col(self):
        return self.db["allocations"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("asset_id", ASCENDING), ("status", ASCENDING)])
        await self.col.create_index([("to_user_id", ASCENDING), ("status", ASCENDING)])
        await self.col.create_index([("created_at", DESCENDING)])

    async def get_by_id(self, allocation_id: ObjectId) -> dict[str, Any] | None:
        return await self.col.find_one({"_id": allocation_id})

    async def get_active_by_asset(self, asset_id: ObjectId) -> dict[str, Any] | None:
        return await self.col.find_one({"asset_id": asset_id, "status": AllocationStatus.active.value})

    async def list(self, user_id: ObjectId | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if user_id:
            query["to_user_id"] = user_id
        cur = self.col.find(query).sort("created_at", DESCENDING).skip(offset).limit(limit)
        return [doc async for doc in cur]

    async def create_allocation(
        self, *, asset_id: ObjectId, to_user_id: ObjectId, notes: str | None, actor_user_id: ObjectId | None
    ) -> dict[str, Any]:
        now = now_utc()
        doc = {
            "asset_id": asset_id,
            "from_user_id": None,
            "to_user_id": to_user_id,
            "status": AllocationStatus.active.value,
            "notes": notes,
            "requested_by": actor_user_id,
            "approved_by": actor_user_id,
            "created_at": now,
            "updated_at": now,
        }
        res = await self.col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def mark_returned(self, allocation_id: ObjectId, notes: str | None) -> dict[str, Any] | None:
        await self.col.update_one(
            {"_id": allocation_id, "status": AllocationStatus.active.value},
            {"$set": {"status": AllocationStatus.returned.value, "notes": notes, "updated_at": now_utc()}},
        )
        return await self.get_by_id(allocation_id)

    async def create_transfer_request(
        self, allocation_id: ObjectId, to_user_id: ObjectId, notes: str | None, requested_by: ObjectId
    ) -> dict[str, Any] | None:
        alloc = await self.get_by_id(allocation_id)
        if not alloc or alloc.get("status") != AllocationStatus.active.value:
            return None

        await self.col.update_one(
            {"_id": allocation_id},
            {
                "$set": {
                    "status": AllocationStatus.pending_transfer.value,
                    "transfer_to_user_id": to_user_id,
                    "transfer_notes": notes,
                    "requested_by": requested_by,
                    "updated_at": now_utc(),
                }
            },
        )
        return await self.get_by_id(allocation_id)

    async def decide_transfer(
        self, allocation_id: ObjectId, decision: str, decided_by: ObjectId, notes: str | None
    ) -> dict[str, Any] | None:
        alloc = await self.get_by_id(allocation_id)
        if not alloc or alloc.get("status") != AllocationStatus.pending_transfer.value:
            return None

        if decision == "reject":
            await self.col.update_one(
                {"_id": allocation_id},
                {"$set": {"status": AllocationStatus.active.value, "decision_notes": notes, "updated_at": now_utc()}},
            )
            return await self.get_by_id(allocation_id)

        # approve -> create a new allocation record and close the old one as transferred
        transfer_to_user_id = alloc.get("transfer_to_user_id")
        if not isinstance(transfer_to_user_id, ObjectId):
            return None

        now = now_utc()
        await self.col.update_one(
            {"_id": allocation_id},
            {"$set": {"status": AllocationStatus.transferred.value, "approved_by": decided_by, "updated_at": now}},
        )
        new_doc = {
            "asset_id": alloc["asset_id"],
            "from_user_id": alloc["to_user_id"],
            "to_user_id": transfer_to_user_id,
            "status": AllocationStatus.active.value,
            "notes": notes,
            "requested_by": alloc.get("requested_by"),
            "approved_by": decided_by,
            "created_at": now,
            "updated_at": now,
        }
        res = await self.col.insert_one(new_doc)
        new_doc["_id"] = res.inserted_id
        return new_doc
