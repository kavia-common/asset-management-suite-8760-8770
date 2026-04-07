from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.security import hash_password, verify_password
from src.api.core.serialization import now_utc
from src.api.models.db_models import User
from src.api.models.schemas import RoleName, UserStatus
from src.api.repositories.base import BaseRepository


class UsersRepository(BaseRepository):
    """PostgreSQL operations for users."""

    def __init__(self, session: AsyncSession = BaseRepository.__init__.__defaults__[0]):  # type: ignore[misc]
        # NOTE: Keeps FastAPI Depends() behavior via BaseRepository; overridden for type clarity.
        super().__init__(session=session)

    async def get_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        stmt = select(User).where(User.id == user_id)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return _user_to_dict(row) if row else None

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        stmt = select(User).where(User.username == username)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return _user_to_dict(row) if row else None

    async def list(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        stmt = select(User).order_by(User.created_at.asc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [_user_to_dict(u) for u in rows]

    async def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str,
        roles: list[RoleName],
    ) -> dict[str, Any]:
        now = now_utc()
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            roles=[r.value for r in roles],
            status=UserStatus.active.value,
            created_at=now,
            updated_at=now,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(user)
        return _user_to_dict(user)

    async def update_user(self, user_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
        updates = dict(updates)
        updates["updated_at"] = now_utc()
        stmt = update(User).where(User.id == user_id).values(**updates).returning(User)
        res = await self.session.execute(stmt)
        await self.session.commit()
        row = res.scalar_one_or_none()
        return _user_to_dict(row) if row else None

    async def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        user = await self.get_by_username(username)
        if not user:
            return None
        if user.get("status") != UserStatus.active.value:
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        return user


def _user_to_dict(u: User) -> dict[str, Any]:
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "password_hash": u.password_hash,
        "roles": u.roles,
        "status": u.status,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
    }
