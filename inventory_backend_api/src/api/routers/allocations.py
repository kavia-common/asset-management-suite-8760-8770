from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.core.serialization import mongo_to_api, to_object_id
from src.api.deps.auth import get_current_user, require_roles
from src.api.models.schemas import (
    AllocateRequest,
    AllocationResponse,
    AuditAction,
    ReturnRequest,
    RoleName,
    TransferDecisionRequest,
    TransferRequestCreate,
)
from src.api.repositories.allocations import AllocationsRepository
from src.api.repositories.assets import AssetsRepository
from src.api.repositories.audits import AuditsRepository
from src.api.repositories.users import UsersRepository

router = APIRouter(prefix="/allocations", tags=["allocations"])


@router.get(
    "",
    response_model=list[AllocationResponse],
    summary="List allocations",
    description="List allocations. Admin sees all; user sees their own allocations by default.",
    operation_id="allocations_list",
)
async def list_allocations(
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
    alloc_repo: AllocationsRepository = Depends(),
    actor: dict = Depends(get_current_user),
) -> list[AllocationResponse]:
    """List allocations."""
    # If not admin, force user_id to self
    if "admin" not in actor.get("roles", []):
        uid = actor["_id"]
    else:
        uid = to_object_id(user_id) if user_id else None

    docs = await alloc_repo.list(user_id=uid, limit=limit, offset=offset)
    return [AllocationResponse(**mongo_to_api(d)) for d in docs]


@router.post(
    "/allocate",
    response_model=AllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate asset",
    description="Admin-only: allocate an asset to a user (creates an active allocation).",
    operation_id="allocations_allocate",
)
async def allocate(
    payload: AllocateRequest,
    alloc_repo: AllocationsRepository = Depends(),
    assets_repo: AssetsRepository = Depends(),
    users_repo: UsersRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> AllocationResponse:
    """Allocate an asset to a user."""
    asset_oid = to_object_id(payload.asset_id)
    user_oid = to_object_id(payload.to_user_id)

    asset = await assets_repo.get_by_id(asset_oid)
    if not asset or not asset.get("active", True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    user = await users_repo.get_by_id(user_oid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    active = await alloc_repo.get_active_by_asset(asset_oid)
    if active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset already allocated")

    doc = await alloc_repo.create_allocation(
        asset_id=asset_oid,
        to_user_id=user_oid,
        notes=payload.notes,
        actor_user_id=actor["_id"],
    )
    await audits_repo.create(
        actor_user_id=actor["_id"],
        action=AuditAction.allocate.value,
        entity_type="allocation",
        entity_id=doc["_id"],
        detail={"allocation": mongo_to_api(doc)},
    )
    return AllocationResponse(**mongo_to_api(doc))


@router.post(
    "/return",
    response_model=AllocationResponse,
    summary="Return asset",
    description="Admin-only: mark an active allocation as returned.",
    operation_id="allocations_return",
)
async def return_asset(
    payload: ReturnRequest,
    alloc_repo: AllocationsRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> AllocationResponse:
    """Return an asset."""
    alloc_oid = to_object_id(payload.allocation_id)
    doc = await alloc_repo.mark_returned(alloc_oid, payload.notes)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found or not active")

    await audits_repo.create(
        actor_user_id=actor["_id"],
        action=AuditAction.return_asset.value,
        entity_type="allocation",
        entity_id=alloc_oid,
        detail={"allocation": mongo_to_api(doc)},
    )
    return AllocationResponse(**mongo_to_api(doc))


@router.post(
    "/transfer",
    response_model=AllocationResponse,
    summary="Request transfer",
    description="Authenticated user: request transfer of an active allocation to another user (status becomes pending_transfer).",
    operation_id="allocations_transfer_request",
)
async def request_transfer(
    payload: TransferRequestCreate,
    alloc_repo: AllocationsRepository = Depends(),
    users_repo: UsersRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(get_current_user),
) -> AllocationResponse:
    """Request a transfer."""
    alloc_oid = to_object_id(payload.allocation_id)
    to_user_oid = to_object_id(payload.to_user_id)

    to_user = await users_repo.get_by_id(to_user_oid)
    if not to_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    doc = await alloc_repo.create_transfer_request(
        allocation_id=alloc_oid, to_user_id=to_user_oid, notes=payload.notes, requested_by=actor["_id"]
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation not active or not found")

    await audits_repo.create(
        actor_user_id=actor["_id"],
        action=AuditAction.transfer_request.value,
        entity_type="allocation",
        entity_id=alloc_oid,
        detail={"allocation": mongo_to_api(doc)},
    )
    return AllocationResponse(**mongo_to_api(doc))


@router.post(
    "/transfer/{allocation_id}/decision",
    response_model=AllocationResponse,
    summary="Approve/reject transfer",
    description="Admin-only: approve or reject a pending transfer.",
    operation_id="allocations_transfer_decision",
)
async def decide_transfer(
    allocation_id: str,
    payload: TransferDecisionRequest,
    alloc_repo: AllocationsRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> AllocationResponse:
    """Approve or reject a transfer request."""
    alloc_oid = to_object_id(allocation_id)
    doc = await alloc_repo.decide_transfer(alloc_oid, payload.decision, actor["_id"], payload.notes)
    if not doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer not pending or allocation not found")

    action = AuditAction.transfer_approve.value if payload.decision == "approve" else AuditAction.transfer_reject.value
    await audits_repo.create(
        actor_user_id=actor["_id"],
        action=action,
        entity_type="allocation",
        entity_id=alloc_oid,
        detail={"result": mongo_to_api(doc)},
    )
    return AllocationResponse(**mongo_to_api(doc))
