from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.security import hash_password
from src.api.core.serialization import now_utc
from src.api.models.db_models import User
from src.api.models.schemas import RoleName, UserStatus


# PUBLIC_INTERFACE
async def ensure_seed_admin(session: AsyncSession) -> None:
    """Ensure at least one admin user exists (idempotent).

    Optional environment variables:
    - SEED_ADMIN_USERNAME (default: admin)
    - SEED_ADMIN_EMAIL (default: admin@example.com)
    - SEED_ADMIN_PASSWORD (default: ChangeMe123!)
    - SEED_ADMIN_FULL_NAME (default: System Admin)
    """
    username = os.getenv("SEED_ADMIN_USERNAME", "admin")
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe123!")
    full_name = os.getenv("SEED_ADMIN_FULL_NAME", "System Admin")

    # If there is any admin already, skip.
    stmt = select(User).where(User.roles.contains([RoleName.admin.value]))  # type: ignore[attr-defined]
    res = await session.execute(stmt)
    existing_admin = res.scalar_one_or_none()
    if existing_admin:
        return

    now = now_utc()
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        roles=[RoleName.admin.value, RoleName.user.value],
        status=UserStatus.active.value,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.commit()
