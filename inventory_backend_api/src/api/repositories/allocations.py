from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.serialization import now_utc
from src.api.models.db_models import Allocation
from src.api.models.schemas import AllocationStatus
from src.api.repositories.base import BaseRepository


class AllocationsRepository(BaseRepository):
    """PostgreSQL operations for allocations and transfer workflow."""

    def __init__(self, session: AsyncSession = BaseRepository.__init__.__defaults__[0]):  # type: ignore[misc]
        super().__init__(session=session)

    async def get_by_id(self, allocation_id: UUID) -> dict[str, Any] | None:
        stmt = select(Allocation).where(Allocation.id == allocation_id)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return _alloc_to_dict(row) if row else None

    async def get_active_by_asset(self, asset_id: UUID) -> dict[str, Any] | None:
        stmt = select(Allocation).where(
            and_(Allocation.asset_id == asset_id, Allocation.status == AllocationStatus.active.value)
        )
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return _alloc_to_dict(row) if row else None

    async def list(self, user_id: UUID | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        stmt = select(Allocation)
        if user_id:
            stmt = stmt.where(Allocation.to_user_id == user_id)
        stmt = stmt.order_by(Allocation.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [_alloc_to_dict(a) for a in rows]

    async def create_allocation(
        self, *, asset_id: UUID, to_user_id: UUID, notes: str | None, actor_user_id: UUID | None
    ) -> dict[str, Any]:
        now = now_utc()
        alloc = Allocation(
            asset_id=asset_id,
            from_user_id=None,
            to_user_id=to_user_id,
            status=AllocationStatus.active.value,
            notes=notes,
            requested_by=actor_user_id,
            approved_by=actor_user_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(alloc)
        await self.session.commit()
        await self.session.refresh(alloc)
        return _alloc_to_dict(alloc)

    async def mark_returned(self, allocation_id: UUID, notes: str | None) -> dict[str, Any] | None:
        stmt = (
            update(Allocation)
            .where(and_(Allocation.id == allocation_id, Allocation.status == AllocationStatus.active.value))
            .values(status=AllocationStatus.returned.value, notes=notes, updated_at=now_utc())
            .returning(Allocation)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        row = res.scalar_one_or_none()
        return _alloc_to_dict(row) if row else None

    async def create_transfer_request(
        self, allocation_id: UUID, to_user_id: UUID, notes: str | None, requested_by: UUID
    ) -> dict[str, Any] | None:
        # Only allow transfer request from active allocation
        alloc = await self.get_by_id(allocation_id)
        if not alloc or alloc.get("status") != AllocationStatus.active.value:
            return None

        stmt = (
            update(Allocation)
            .where(Allocation.id == allocation_id)
            .values(
                status=AllocationStatus.pending_transfer.value,
                transfer_to_user_id=to_user_id,
                transfer_notes=notes,
                requested_by=requested_by,
                updated_at=now_utc(),
            )
            .returning(Allocation)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        row = res.scalar_one_or_none()
        return _alloc_to_dict(row) if row else None

    async def decide_transfer(
        self, allocation_id: UUID, decision: str, decided_by: UUID, notes: str | None
    ) -> dict[str, Any] | None:
        alloc_obj_stmt = select(Allocation).where(Allocation.id == allocation_id)
        res = await self.session.execute(alloc_obj_stmt)
        alloc = res.scalar_one_or_none()
        if not alloc or alloc.status != AllocationStatus.pending_transfer.value:
            return None

        if decision == "reject":
            stmt = (
                update(Allocation)
                .where(Allocation.id == allocation_id)
                .values(
                    status=AllocationStatus.active.value,
                    decision_notes=notes,
                    updated_at=now_utc(),
                )
                .returning(Allocation)
            )
            res2 = await self.session.execute(stmt)
            await self.session.commit()
            row = res2.scalar_one_or_none()
            return _alloc_to_dict(row) if row else None

        # approve -> close old allocation as transferred and create a new active allocation
        if alloc.transfer_to_user_id is None:
            return None

        now = now_utc()
        # 1) mark old as transferred
        stmt = (
            update(Allocation)
            .where(Allocation.id == allocation_id)
            .values(status=AllocationStatus.transferred.value, approved_by=decided_by, updated_at=now)
            .returning(Allocation)
        )
        await self.session.execute(stmt)

        # 2) create new allocation
        new_alloc = Allocation(
            asset_id=alloc.asset_id,
            from_user_id=alloc.to_user_id,
            to_user_id=alloc.transfer_to_user_id,
            status=AllocationStatus.active.value,
            notes=notes,
            requested_by=alloc.requested_by,
            approved_by=decided_by,
            created_at=now,
            updated_at=now,
        )
        self.session.add(new_alloc)
        await self.session.commit()
        await self.session.refresh(new_alloc)
        return _alloc_to_dict(new_alloc)


def _alloc_to_dict(a: Allocation) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "asset_id": str(a.asset_id),
        "from_user_id": str(a.from_user_id) if a.from_user_id else None,
        "to_user_id": str(a.to_user_id),
        "status": a.status,
        "notes": a.notes,
        "requested_by": str(a.requested_by) if a.requested_by else None,
        "approved_by": str(a.approved_by) if a.approved_by else None,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }
