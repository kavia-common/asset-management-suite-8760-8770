from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import ASCENDING

from src.api.core.security import hash_password, verify_password
from src.api.core.serialization import now_utc
from src.api.models.schemas import RoleName, UserStatus
from src.api.repositories.base import BaseRepository


class UsersRepository(BaseRepository):
    """MongoDB operations for users."""

    @property
    def col(self):
        return self.db["users"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("username", ASCENDING)], unique=True)
        await self.col.create_index([("email", ASCENDING)], unique=True)

    async def get_by_id(self, user_id: ObjectId) -> dict[str, Any] | None:
        return await self.col.find_one({"_id": user_id})

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        return await self.col.find_one({"username": username})

    async def list(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        cur = self.col.find({}).sort("created_at", ASCENDING).skip(offset).limit(limit)
        return [doc async for doc in cur]

    async def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str,
        roles: list[RoleName],
    ) -> dict[str, Any]:
        now = now_utc()
        doc = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "password_hash": hash_password(password),
            "roles": [r.value for r in roles],
            "status": UserStatus.active.value,
            "created_at": now,
            "updated_at": now,
        }
        res = await self.col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def update_user(self, user_id: ObjectId, updates: dict[str, Any]) -> dict[str, Any] | None:
        updates["updated_at"] = now_utc()
        await self.col.update_one({"_id": user_id}, {"$set": updates})
        return await self.get_by_id(user_id)

    async def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        user = await self.get_by_username(username)
        if not user:
            return None
        if user.get("status") != UserStatus.active.value:
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        return user
