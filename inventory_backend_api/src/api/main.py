from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import get_settings
from src.api.core.db import close_postgres, connect_to_postgres
from src.api.core.migrations import run_migrations
from src.api.core.seed import ensure_seed_admin
from src.api.routers.allocations import router as allocations_router
from src.api.routers.assets import router as assets_router
from src.api.routers.audits import router as audits_router
from src.api.routers.auth import router as auth_router
from src.api.routers.users import router as users_router

openapi_tags = [
    {"name": "auth", "description": "Authentication and token issuance."},
    {"name": "users", "description": "User and role management."},
    {"name": "assets", "description": "Asset/device CRUD and search."},
    {"name": "allocations", "description": "Allocation, returns, and transfer workflow."},
    {"name": "audits", "description": "Audit log access."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan.

    - Connects to PostgreSQL (async SQLAlchemy)
    - Runs migrations (create/update schema)
    - Ensures a bootstrap admin user exists (idempotent seed)
    """
    pg = await connect_to_postgres()
    app.state.postgres = pg

    # Apply schema
    await run_migrations(pg.engine)

    # Ensure an initial admin exists for first login (optional env overrides).
    async with pg.sessionmaker() as session:
        await ensure_seed_admin(session)

    yield

    await close_postgres(pg)


settings = get_settings()

app = FastAPI(
    title="Inventory / Asset Management API",
    description=(
        "Secure backend API for asset inventory management: authentication, user/role management, "
        "asset/device registry, allocation + transfer workflows, and audit logging."
    ),
    version="0.3.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# CORS
# Important: when allow_credentials=True, Starlette/FastAPI cannot use allow_origins=["*"].
# So we only enable credentials when origins are explicitly set.
allow_origins = (
    [o.strip() for o in (settings.allowed_origins or "").split(",") if o.strip()]
    if settings.allowed_origins != "*"
    else ["*"]
)
allow_methods = (
    [m.strip() for m in (settings.allowed_methods or "*").split(",")]
    if settings.allowed_methods != "*"
    else ["*"]
)
allow_headers = (
    [h.strip() for h in (settings.allowed_headers or "*").split(",")]
    if settings.allowed_headers != "*"
    else ["*"]
)

allow_credentials = allow_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)


@app.get(
    "/",
    summary="Health check",
    description="Simple health check endpoint.",
    tags=["health"],
    operation_id="health_check",
)
def health_check():
    """Health check.

    Returns:
    - message: status
    """
    return {"message": "Healthy"}


@app.get(
    "/docs/help",
    summary="API usage help",
    description="Notes about authentication and common workflows.",
    tags=["docs"],
    operation_id="docs_help",
)
def docs_help():
    """Provide quick usage notes for developers."""
    return {
        "auth": {"how_to": "POST /auth/login with username/password, then use Authorization: Bearer <token>"},
        "workflow": {
            "allocate": "Admin: POST /allocations/allocate",
            "return": "Admin: POST /allocations/return",
            "transfer": "User: POST /allocations/transfer then Admin: POST /allocations/transfer/{id}/decision",
        },
    }


# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(assets_router)
app.include_router(allocations_router)
app.include_router(audits_router)
