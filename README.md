# Asset Management Suite (Backend Workspace)

This workspace contains the **FastAPI backend** container: `inventory_backend_api`.

The full system also includes:
- `inventory_react_frontend` (React, port `3000`) in workspace `asset-management-suite-8760-8771`
- `inventory_postgresql_db` (**PostgreSQL**, port `5001`) in workspace `asset-management-suite-8760-8769`

## Ports / URLs (local dev defaults)

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:3001`
- PostgreSQL: provided via env vars `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (DB container exposes them)

## Backend environment variables

Create a `.env` file in `inventory_backend_api/` (do not commit secrets). Required:

- `POSTGRES_HOST` (from DB container)
- `POSTGRES_PORT` (from DB container)
- `POSTGRES_DB` (from DB container)
- `POSTGRES_USER` (from DB container)
- `POSTGRES_PASSWORD` (from DB container)
- `JWT_SECRET` (set to a strong random string)
- `ALLOWED_ORIGINS` (recommended for local dev: `http://localhost:3000`)

Optional:
- `ALLOWED_METHODS` (default `*`)
- `ALLOWED_HEADERS` (default `*`)
- `ACCESS_TOKEN_EXP_MINUTES` (default `60`)
- `BACKEND_URL` (e.g. `http://localhost:3001`)
- `FRONTEND_URL` (e.g. `http://localhost:3000`)

### CORS note

If you set `ALLOWED_ORIGINS="*"`, the backend will disable `allow_credentials` automatically.
For browser apps using `Authorization: Bearer ...`, you should set explicit origins, e.g.:

- `ALLOWED_ORIGINS=http://localhost:3000`

## Run backend locally

From `asset-management-suite-8760-8770/inventory_backend_api`:

1. Install dependencies
   - `pip install -r requirements.txt`

2. Run API (dev)
   - `uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload`

3. Verify
   - `GET http://localhost:3001/` -> `{ "message": "Healthy" }`
   - OpenAPI: `http://localhost:3001/docs`

## End-to-end local run (frontend + backend + DB)

1. Start DB container (`inventory_postgresql_db`, PostgreSQL)
   - Ensure it is running and note exported env vars:
     - `POSTGRES_HOST`
     - `POSTGRES_PORT`
     - `POSTGRES_DB`
     - `POSTGRES_USER`
     - `POSTGRES_PASSWORD`

2. Start backend (`inventory_backend_api`)
   - Set `.env` with `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET`, `ALLOWED_ORIGINS=http://localhost:3000`
   - Start on port `3001`

3. Start frontend (`inventory_react_frontend`)
   - In `inventory_react_frontend`, set:
     - `REACT_APP_API_BASE_URL=http://localhost:3001`
   - Run: `npm start` (port `3000`)

## Common flow

1. Login: `POST /auth/login`
2. Use returned token with: `Authorization: Bearer <token>`
3. Admin:
   - Create users: `POST /users`
   - Create assets: `POST /assets`
   - Allocate/return/approve transfers via `/allocations/*`
4. Audit logs: `GET /audits` (admin)
