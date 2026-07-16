# Development

> **Status:** Phase 0. Sections marked _(Phase N)_ are placeholders.

---

## Prerequisites

| Tool    | Version | Notes                                                         |
| ------- | ------- | ------------------------------------------------------------- |
| Node.js | 20+     | 20 is what CI uses.                                           |
| Python  | 3.12+   | `python3` may point at an older version — check `python3 -V`. |
| git     | any     |                                                               |

## First-time setup

```bash
git clone https://github.com/Pranavsingh431/vayu_console.git
cd vayu_console

# Frontend and shared packages. Run from the root: npm workspaces hoists
# dependencies, so installing inside apps/web instead will not work correctly.
npm install

# Backend, in its own virtualenv.
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ../..

# Environment files (optional in Phase 0).
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
```

Phase 0 needs no configuration. Leave `DATABASE_URL` and the API keys blank; `/health`
reports them as `not_configured` and the app runs.

## Running

```bash
npm run dev:api     # http://localhost:8000, reloads on change
npm run dev:web     # http://localhost:3000, reloads on change
```

`dev:api` expects the virtualenv at `apps/api/.venv`. If you keep yours elsewhere, run
`uvicorn app.main:app --reload --port 8000` from `apps/api` directly.

**Port 8000 already in use?** Start the API on another port and point the web app at it:

```bash
cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8001
# then, in apps/web/.env.local:
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

## Checks

Everything below runs in CI. Run it locally before pushing and CI holds no surprises.

### Frontend (from the repository root)

```bash
npm run format:check   # prettier
npm run format         # prettier, writing fixes
npm run lint           # eslint
npm run typecheck      # tsc --noEmit
npm run build          # next build
```

### Backend (from `apps/api`)

```bash
.venv/bin/ruff check .          # lint
.venv/bin/ruff check --fix .    # lint, writing fixes
.venv/bin/black .               # format
.venv/bin/mypy app tests        # types (strict)
.venv/bin/pytest                # tests
```

### Secrets

```bash
scripts/check-secrets.sh
```

Fails if an environment file or credential pattern is tracked by git. This repository is
public and `.env` holds live keys, so treat a failure here as urgent.

The same check is available as a pre-commit hook, which catches a mistake before it reaches
history rather than after. Enable it once per clone — git does not do this automatically,
because a repository cannot be allowed to run code on checkout:

```bash
git config core.hooksPath .githooks
```

## Conventions

**Python** — Ruff and Black, 100 columns, `mypy --strict`. Type annotations are required;
`from __future__ import annotations` at the top of each module.

**TypeScript** — Prettier and ESLint, 100 columns, strict mode. Prefer `type` imports.
No `any`.

**Layering** (see [architecture.md](architecture.md)) — routes delegate to services;
services never write raw SQL; repositories own all queries. A route with a database query
in it will be sent back at review.

**Commits** — imperative mood, explain the why. Conventional Commits prefixes
(`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`) are encouraged.

## Adding things

### A shadcn/ui component

```bash
cd apps/web
npx shadcn@latest add <component>
```

Lands in `src/components/ui/`. It is your code now — edit it freely.

### An API endpoint

1. Schema in `app/schemas/`.
2. Logic in `app/services/`.
3. Route in `app/api/routes/`, registered in `app/api/router.py`.
4. Mirror the response type in `packages/shared/src/types/` so the frontend stays in sync.
5. Test in `apps/api/tests/`.

### A dependency

- Python → `apps/api/pyproject.toml`, then `pip install -e ".[dev]"`.
- Node → `npm install <pkg> --workspace=@vayu/web` from the root.

## Database

_(Phase 1)_ No application tables exist yet.

```bash
cd apps/api
.venv/bin/alembic upgrade head                        # apply migrations
.venv/bin/alembic revision --autogenerate -m "..."    # create a migration
.venv/bin/alembic history                             # list revisions
.venv/bin/alembic upgrade head --sql                  # print SQL, no connection
```

Anything except `history` and offline `--sql` needs `DATABASE_URL` set.

Autogenerate only sees models imported in `app/models/__init__.py`. A model that is not
imported there is invisible to it and will be silently omitted.

Always read a generated migration before applying it.

## Testing

```bash
cd apps/api
.venv/bin/pytest                       # all
.venv/bin/pytest tests/test_health.py  # one file
.venv/bin/pytest -k health             # by name
.venv/bin/pytest -vv                   # verbose
```

Tests run against the app through `httpx.ASGITransport` — no network, no live server.
Fixtures live in `tests/conftest.py` and pass `_env_file=None`, so your local `.env` cannot
change a test result.

_(Later phase)_ Frontend tests. There is no meaningful UI logic to test in Phase 0.

## Editor

VS Code settings and recommended extensions are committed under `.vscode/`. Accept the
extension prompt on first open. Format-on-save is configured: Prettier for TS/CSS/MD,
Black for Python, with Ruff organising imports.

Point your editor's Python interpreter at `apps/api/.venv/bin/python`.

## Troubleshooting

| Symptom                                    | Cause and fix                                                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Status page: "API unreachable"             | The API is not running, or is on a different port. Start `npm run dev:api`.              |
| `/health` shows `database: not_configured` | Expected in Phase 0. Set `DATABASE_URL` if you want a live check.                        |
| `/health` shows `database: unavailable`    | `DATABASE_URL` is set but wrong or unreachable. The `detail` field names the error type. |
| CORS error in the browser console          | The web origin is missing from `CORS_ORIGINS` on the API.                                |
| `address already in use` on :8000          | Another process owns the port. See "Port 8000 already in use?" above.                    |
| `npm run dev:api` — no such file           | The virtualenv is missing. Recreate it (see First-time setup).                           |
| Alembic: `DATABASE_URL is not set`         | Expected. Migrations need a real database.                                               |
| mypy passes locally but fails in CI        | CI runs `mypy app tests`. Run the same, not just `mypy app`.                             |
