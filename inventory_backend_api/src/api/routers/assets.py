from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.core.serialization import mongo_to_api, to_object_id
from src.api.deps.auth import get_current_user, require_roles
from src.api.models.schemas import AssetCreateRequest, AssetResponse, AssetUpdateRequest, RoleName
from src.api.repositories.assets import AssetsRepository
from src.api.repositories.audits import AuditsRepository

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get(
    "",
    response_model=list[AssetResponse],
    summary="List assets",
    description="List assets/devices. Any authenticated user can view assets.",
    operation_id="assets_list",
)
async def list_assets(
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    assets_repo: AssetsRepository = Depends(),
    _: dict = Depends(get_current_user),
) -> list[AssetResponse]:
    """List assets."""
    docs = await assets_repo.list(q=q, limit=limit, offset=offset)
    return [AssetResponse(**mongo_to_api(d)) for d in docs]


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create asset",
    description="Admin-only: create a new asset/device.",
    operation_id="assets_create",
)
async def create_asset(
    payload: AssetCreateRequest,
    assets_repo: AssetsRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> AssetResponse:
    """Create asset."""
    existing = await assets_repo.get_by_asset_tag(payload.asset_tag)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="asset_tag already exists")

    doc = await assets_repo.create(payload.model_dump())
    await audits_repo.create(
        actor_user_id=actor["_id"], action="create", entity_type="asset", entity_id=to_object_id(mongo_to_api(doc)["id"]), detail={}
    )
    return AssetResponse(**mongo_to_api(doc))


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Update asset",
    description="Admin-only: update asset/device fields.",
    operation_id="assets_update",
)
async def update_asset(
    asset_id: str,
    payload: AssetUpdateRequest,
    assets_repo: AssetsRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> AssetResponse:
    """Update asset."""
    oid = to_object_id(asset_id)
    updates = payload.model_dump(exclude_unset=True)
    doc = await assets_repo.update(oid, updates)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    await audits_repo.create(actor_user_id=actor["_id"], action="update", entity_type="asset", entity_id=oid, detail={"updates": updates})
    return AssetResponse(**mongo_to_api(doc))
