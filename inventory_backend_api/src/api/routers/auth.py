from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.core.security import create_access_token
from src.api.core.serialization import to_uuid
from src.api.models.schemas import LoginRequest, TokenResponse
from src.api.repositories.audits import AuditsRepository
from src.api.repositories.users import UsersRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate user using username/password and return a JWT access token.",
    operation_id="auth_login",
)
async def login(
    payload: LoginRequest,
    users_repo: UsersRepository = Depends(),
    audits_repo: AuditsRepository = Depends(),
) -> TokenResponse:
    """Login endpoint.

    Parameters:
    - payload: username and password

    Returns:
    - access token
    """
    user = await users_repo.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user["id"]), extra_claims={"roles": user.get("roles", [])})
    await audits_repo.create(
        actor_user_id=to_uuid(user["id"]),
        action="login",
        entity_type="user",
        entity_id=to_uuid(user["id"]),
        detail={"user": {"id": user["id"], "username": user["username"], "email": user["email"]}},
    )
    return TokenResponse(access_token=token)
