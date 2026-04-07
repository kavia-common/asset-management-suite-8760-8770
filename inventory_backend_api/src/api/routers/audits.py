from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.core.serialization import mongo_to_api
from src.api.deps.auth import require_roles
from src.api.models.schemas import AuditLogResponse, RoleName
from src.api.repositories.audits import AuditsRepository

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get(
    "",
    response_model=list[AuditLogResponse],
    summary="List audit logs",
    description="Admin-only: list audit log entries.",
    operation_id="audits_list",
)
async def list_audits(
    limit: int = 200,
    offset: int = 0,
    audits_repo: AuditsRepository = Depends(),
    _: dict = Depends(require_roles(RoleName.admin)),
) -> list[AuditLogResponse]:
    """List audits."""
    docs = await audits_repo.list(limit=limit, offset=offset)
    return [AuditLogResponse(**mongo_to_api(d)) for d in docs]
