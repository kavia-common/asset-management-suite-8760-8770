from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.serialization import now_utc
from src.api.models.db_models import Asset
from src.api.repositories.base import BaseRepository


class AssetsRepository(BaseRepository):
    """PostgreSQL operations for assets/devices."""

    def __init__(self, session: AsyncSession = BaseRepository.__init__.__defaults__[0]):  # type: ignore[misc]
        super().__init__(session=session)

    async def get_by_id(self, asset_id: UUID) -> dict[str, Any] | None:
        stmt = select(Asset).where(Asset.id == asset_id)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return _asset_to_dict(row) if row else None

    async def get_by_asset_tag(self, asset_tag: str) -> dict[str, Any] | None:
        stmt = select(Asset).where(Asset.asset_tag == asset_tag)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return _asset_to_dict(row) if row else None

    async def list(self, q: str | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        stmt = select(Asset).where(Asset.active.is_(True))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Asset.asset_tag.ilike(like), Asset.serial_number.ilike(like)))
        stmt = stmt.order_by(Asset.created_at.asc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [_asset_to_dict(a) for a in rows]

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        now = now_utc()
        asset = Asset(
            asset_tag=doc["asset_tag"],
            serial_number=doc.get("serial_number"),
            type=doc["type"],
            manufacturer=doc.get("manufacturer"),
            model=doc.get("model"),
            description=doc.get("description"),
            location=doc.get("location"),
            metadata=doc.get("metadata") or {},
            active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(asset)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(asset)
        return _asset_to_dict(asset)

    async def update(self, asset_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
        updates = dict(updates)
        updates["updated_at"] = now_utc()
        stmt = update(Asset).where(Asset.id == asset_id).values(**updates).returning(Asset)
        res = await self.session.execute(stmt)
        await self.session.commit()
        row = res.scalar_one_or_none()
        return _asset_to_dict(row) if row else None


def _asset_to_dict(a: Asset) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "asset_tag": a.asset_tag,
        "serial_number": a.serial_number,
        "type": a.type,
        "manufacturer": a.manufacturer,
        "model": a.model,
        "description": a.description,
        "location": a.location,
        "metadata": a.metadata or {},
        "active": a.active,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }
