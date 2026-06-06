# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependency management uses `uv`. The `Makefile` wraps the most common workflows:

```powershell
uv sync                                              # install (also: make install)
make api                                             # uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
make worker                                          # uv run python -m src.worker.main
make test                                            # uv run pytest
make lint                                            # uv run ruff check .
make format                                          # uv run ruff format .
make check                                           # ruff check + pytest

uv run pytest tests/unit/domains/auth/test_service.py            # single file
uv run pytest tests/integration/test_auth_api.py::test_login     # single test
uv run pytest -k "auth and not integration"                      # by keyword

docker compose up db -d                              # local Postgres (pgvector/pgvector:pg16) on :5432
docker compose up                                    # full stack (api + worker + db)
```

Python 3.11+. Ruff is configured in `pyproject.toml` (line length 100, rules `E,F,I,B,UP`). `pytest-asyncio` runs in `asyncio_mode = "auto"`.

## Environment

Copy `.env.example` to `.env`. Connection is built from `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`; setting `DATABASE_URL` overrides the composition. Auth needs `auth_secret_key` and `auth_token_expire_minutes` (see `src/app/core/config.py`). Tables are created at startup via SQLAlchemy `create_all` — there are no Alembic migrations yet.

## Architecture

The actual layout differs from `README.md` / `docs/architecture.md` (which still describe an earlier `src/modules`, `src/worker`, `src/integrations`, `src/messaging` split). What exists today:

```
src/app/
├── main.py              # FastAPI app, lifespan creates tables, registers domain-exception handlers
├── api/v1/
│   ├── router.py        # mounts every domain router under /v1
│   ├── dependencies.py  # DbDep, CurrentUserDep, requer_papel(...) RBAC dep factory
│   └── health.py
├── core/                # config (pydantic-settings), enums, exceptions, logging, middleware, security (JWT)
├── db/                  # SQLAlchemy Base, DatabaseSessionManager, mixins
│   └── base.py          # MUST import every domain's models so create_all() sees them
└── domains/             # one package per business module (auth, clientes, faturas,
                         # documental, auditoria, regulatorio, recuperacao)
```

Each `domains/<name>/` follows the same five-file convention: `models.py` (SQLAlchemy ORM), `schemas.py` (Pydantic I/O), `repository.py` (DB access), `service.py` (use cases), `router.py` (FastAPI). When adding a new domain you must:

1. Create the package with those five files.
2. Add `from src.app.domains.<name>.models import *` in `src/app/db/base.py` so tables are registered.
3. Mount the router in `src/app/api/v1/router.py` (a single domain can expose multiple routers — see `auditoria` exporting `achados_router`, `validacoes_router`, `fatura_validacoes_router`, and `clientes` exporting `clientes_router`, `distribuidoras_router`, `lotes_router`).

### Error model

Services raise the domain exceptions in `src/app/core/exceptions.py` (`NaoEncontradoError`, `ConflitoDuplicidadeError`, `RegraVioladaError`, `AcessoNegadoError`, `CredenciaisInvalidasError`, `IntegrationError`). `main.py` maps these to HTTP 404/409/422/403/401/502. Do not raise `HTTPException` from services — raise a domain exception and let the handler translate it. Router-level auth checks may still raise `HTTPException` directly (see `dependencies.py`).

### Auth and RBAC

`get_current_user` decodes a Bearer JWT via `TokenService` and resolves a `UsuarioAutenticado`. Use `CurrentUserDep` for "any authenticated user" and `Depends(requer_papel(PapelUsuario.X, ...))` from `dependencies.py` to restrict by role.

### DB sessions

`get_session_manager()` is `lru_cache`d and reads `settings.resolved_database_url`. Routes receive a session via `DbDep` (which yields from `get_db()`); the lifespan disposes the engine on shutdown. PostgreSQL is required (uses `pgvector` extension via the `pgvector/pgvector:pg16` image).

## Notes on stale docs

`README.md` still documents legacy `/v1/users` and `/v1/ai-demo/*` endpoints and references `src/modules`, `src/worker`, `src/integrations`, `src/messaging` — none of these exist in the current tree. Prefer reading `src/app/api/v1/router.py` and the `domains/` packages over the README when answering "what endpoints exist".
