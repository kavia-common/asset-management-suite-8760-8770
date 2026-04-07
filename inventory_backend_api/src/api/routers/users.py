from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.core.serialization import to_uuid
from src.api.deps.auth import get_current_user, require_roles
from src.api.models.schemas import RoleName, UserCreateRequest, UserResponse, UserUpdateRequest
from src.api.repositories.audits import AuditsRepository
from src.api.repositories.users import UsersRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Return the currently authenticated user profile.",
    operation_id="users_me",
)
async def me(user: dict = Depends(get_current_user)) -> UserResponse:
    """Get current user profile."""
    return UserResponse(**_user_api(user))


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List users",
    description="Admin-only: list users.",
    operation_id="users_list",
)
async def list_users(
    limit: int = 100,
    offset: int = 0,
    users_repo: UsersRepository = Depends(),
    _: dict = Depends(require_roles(RoleName.admin)),
) -> list[UserResponse]:
    """List users."""
    docs = await users_repo.list(limit=limit, offset=offset)
    return [UserResponse(**_user_api(d)) for d in docs]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Admin-only: create a new user.",
    operation_id="users_create",
)
async def create_user(
    payload: UserCreateRequest,
    users_repo: UsersRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> UserResponse:
    """Create user."""
    doc = await users_repo.create_user(
        username=payload.username,
        email=str(payload.email),
        full_name=payload.full_name,
        password=payload.password,
        roles=payload.roles,
    )
    await audits_repo.create(
        actor_user_id=to_uuid(actor["id"]),
        action="create",
        entity_type="user",
        entity_id=to_uuid(doc["id"]),
        detail={"user": {"id": doc["id"], "username": doc["username"], "email": doc["email"]}},
    )
    return UserResponse(**_user_api(doc))


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Admin-only: update user fields (roles/status/profile).",
    operation_id="users_update",
)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    users_repo: UsersRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
    actor: dict = Depends(require_roles(RoleName.admin)),
) -> UserResponse:
    """Update user."""
    uid = to_uuid(user_id)
    updates = payload.model_dump(exclude_unset=True)
    if "roles" in updates and updates["roles"] is not None:
        updates["roles"] = [r.value for r in updates["roles"]]

    doc = await users_repo.update_user(uid, updates)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await audits_repo.create(
        actor_user_id=to_uuid(actor["id"]),
        action="update",
        entity_type="user",
        entity_id=uid,
        detail={"updates": updates},
    )
    return UserResponse(**_user_api(doc))


def _user_api(doc: dict) -> dict:
    return {
        **doc,
        "created_at": doc["created_at"].isoformat(),
        "updated_at": doc["updated_at"].isoformat(),
    }
