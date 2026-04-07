from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.core.serialization import to_uuid
from src.api.core.security import decode_token
from src.api.models.schemas import RoleName, UserStatus
from src.api.repositories.users import UsersRepository

_bearer = HTTPBearer(auto_error=False)


# PUBLIC_INTERFACE
async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    users_repo: UsersRepository = Depends(),
) -> dict:
    """Return the current authenticated user document.

    Raises 401 if missing/invalid token.
    """
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        claims = decode_token(creds.credentials)
        user_id = claims.get("sub")
        if not user_id:
            raise ValueError("missing sub")
        uid = to_uuid(user_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await users_repo.get_by_id(uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.get("status") == UserStatus.disabled.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
    return user


# PUBLIC_INTERFACE
def require_roles(*roles: RoleName):
    """Dependency factory enforcing that current user has at least one of the required roles."""

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        user_roles = set(user.get("roles", []))
        required = {r.value for r in roles}
        if not user_roles.intersection(required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _checker
