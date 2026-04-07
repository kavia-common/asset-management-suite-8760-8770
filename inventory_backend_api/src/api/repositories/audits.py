from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.serialization import now_utc
from src.api.models.db_models import Audit
from src.api.repositories.base import BaseRepository


class AuditsRepository(BaseRepository):
    """PostgreSQL operations for audit logs."""

    def __init__(self, session: AsyncSession = BaseRepository.__init__.__defaults__[0]):  # type: ignore[misc]
        super().__init__(session=session)

    async def create(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        detail: dict[str, Any],
    ) -> None:
        audit = Audit(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            created_at=now_utc(),
        )
        self.session.add(audit)
        await self.session.commit()

    async def list(self, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        stmt = select(Audit).order_by(Audit.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [_audit_to_dict(a) for a in rows]


def _audit_to_dict(a: Audit) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "actor_user_id": str(a.actor_user_id) if a.actor_user_id else None,
        "action": a.action,
        "entity_type": a.entity_type,
        "entity_id": str(a.entity_id) if a.entity_id else None,
        "detail": a.detail or {},
        "created_at": a.created_at,
    }
