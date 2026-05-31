# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Backend (from backend/)
pip install -r requirements.txt                    # Install dependencies
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Dev server
python seed.py                                     # Seed sample data (idempotent)

# Frontend (from frontend/)
npm install                                        # Install dependencies
npm run dev                                        # Vite dev server on :5173
npm run build                                      # Production build

# Database migrations (from backend/)
alembic revision --autogenerate -m "description"   # Generate new migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                               # Rollback one step
```

## Architecture Overview

**Stack**: FastAPI (Python) + React 19 + Ant Design 6 + SQLite + JWT auth.

**Request flow**: Browser → Vite dev server (`:5173`) → proxy `/api` → FastAPI (`:8000`). The Vite proxy rewrites 307 redirect Location headers so redirects don't bypass the proxy. The frontend axios interceptor proactively adds trailing slashes to avoid redirects.

**Database**: SQLite with WAL mode enabled (`PRAGMA journal_mode=WAL`). On each connection: foreign keys are enforced and `busy_timeout=5000ms` prevents immediate locking errors. `check_same_thread=False` is set for FastAPI threading. Note: Alembic migration files exist but have empty bodies — actual schema management is done by `Base.metadata.create_all()` on startup (development only).

**Auth**: JWT tokens (HS256, 30min) stored in `localStorage`. Five roles with hierarchical access: `admin` > `system_admin` > `data_admin` > `data_entry` > `reviewer`. The `require_role(*roles)` dependency factory checks permissions; routes declare minimum role required.

## Key Modules

### Backend Routers (prefixes)
- `/api/auth` — Login, token refresh, password change
- `/api/directories` — Tree CRUD. Self-referential `parent_id` builds a hierarchy. Directory tree has self-referential FK; delete blocked if children exist.
- `/api/fields` — CRUD + Excel import/export. Supports filter by sensitivity, domain, anomaly, status. Soft-delete sets `status=inactive`.
- `/api/mappings` — Many-to-many between directories ↔ fields via `directory_field_mappings` table. Supports batch create/delete, AI auto-map, ECharts visualization data, stats.
- `/api/reviews` — Human review workflow. Two types: `anomaly` (auto-detected) and `ai_mapping` (AI suggestions). Approving an AI mapping creates the actual `DirectoryFieldMapping`.
- `/api/reports` — Aggregation endpoints: summary stats, by-directory counts, by-sensitivity distribution, Excel exports.
- `/api/users` — Admin-only user management. Reset password sets `admin123`.
- `/api/logs` — Operation log query (log_service exists but is **not wired** into most CRUD routes — logs are not actively recorded).

### Services
- `llm_service.py` — Calls Qwen (`qwen-plus`) via DashScope API (OpenAI-compatible SDK). Sends directory tree + unmapped fields as Chinese prompt, parses JSON response.
- `excel_service.py` — Template generation, parsing, and import orchestration with per-row validation.
- `anomaly_detector.py` — Two rules: unmapped fields (no mapping exists) and missing info (null data_type/table_name/name). Creates `ReviewRecord` entries, marks `is_anomaly=True`.
- `log_service.py` — Available but not imported in route handlers. To enable logging, import and call `log_action()` in each route.

### Frontend Pages
- `/` — Dashboard (stat cards + recent logs)
- `/directories` — Tree view + detail/edit panel
- `/fields` — Table with search/filter + drawer form + Excel import modal
- `/mappings` — Tabs: list (with auto-map panel + batch dialog) + ECharts force graph
- `/review` — Tabs: anomaly review + AI mapping review (approve/reject drawer)
- `/users` — Admin-only user CRUD
- `/logs` — Filterable log table with date range
- `/reports` — Charts (bar, pie) + Excel exports

## Patterns and Conventions

- **No trailing slash on resource URL = 307 redirect**. The frontend interceptor adds `/` to single-segment URLs (e.g., `/fields` → `/fields/`) to avoid the redirect. If a redirect does fire, the Vite proxy rewrites the Location header to stay in-proxy.
- **Soft deletion**: Fields set `status=inactive`; directories set `is_active=False`; users set `is_active=False`. No hard deletes.
- **Idempotent seed**: `seed.py` checks counts before inserting — safe to run multiple times.
- **AI is human-in-the-loop**: Auto-map creates `ReviewRecord` entries (not direct mappings). A reviewer must approve before the `DirectoryFieldMapping` is created.
- **Frontend auth check**: `hasRole(...roles)` from `useAuth()` hook filters UI elements. `ProtectedRoute` handles redirect. Each page calls its data regardless of roles — the backend is the enforcement point.
- **Config**: All settings in `app/core/config.py` via `pydantic-settings`, reads `.env`. API keys go in `.env`, never in code.

## Gotchas

- **Alembic migrations are empty**: `Base.metadata.create_all()` handles schema in dev. For production, populate migration bodies or switch to a proper migration workflow.
- **Operation logging is not active**: `log_service.py` is defined but no CRUD route calls it. If audit logging matters, wire it into each route handler.
- **SQLite in production**: WAL mode helps concurrency but single-server only. For multi-process deployment, switch to PostgreSQL.
- **CORS is restrictive**: Only `localhost:5173` is allowed. If a different frontend port or domain is needed, update `allow_origins` in `main.py`.
- **WAL files**: `*.db-*` is in `.gitignore`. WAL creates `-shm` and `-wal` files alongside the database — these are transient SQLite internals.
