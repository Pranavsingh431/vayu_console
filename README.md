# Vayu Console

**Urban Air Quality Decision Intelligence**

An AI-powered air quality decision-support platform for municipal officers in Delhi.

Vayu Console is not a consumer AQI dashboard. It exists to help municipal authorities act:
identify pollution hotspots, infer likely source contributions from physically grounded
evidence, recommend interventions backed by historical analogues, and show explainable
evidence for every recommendation.

Scope for this sprint is **Delhi only**.

---

## Status

Phase 0 — repository foundation. The API exposes `/health` and `/version`; the web app
serves a landing page and a status page. No air quality features exist yet, by design.

---

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  apps/web    │  HTTPS  │  apps/api    │         │   Supabase   │
│  Next.js 15  ├────────►│   FastAPI    ├────────►│  PostgreSQL  │
│  (Vercel)    │  JSON   │  (Render)    │  SQL    │  + PostGIS   │
└──────────────┘         └──────┬───────┘         └──────────────┘
                                │
                                │ (later phases)
                                ▼
                         ┌──────────────┐
                         │    Redis     │
                         │    cache     │
                         └──────────────┘
```

Both apps share types from `packages/shared`, so an API schema change surfaces as a
frontend type error rather than a runtime surprise.

See [docs/architecture.md](docs/architecture.md) for detail.

### Stack

| Layer    | Choice                                                             |
| -------- | ------------------------------------------------------------------ |
| Frontend | Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui, TanStack Query |
| Mapping  | MapLibre GL, deck.gl _(later phases)_                              |
| Backend  | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic           |
| Database | Supabase PostgreSQL + PostGIS                                      |
| Cache    | Redis _(designed for, not yet connected)_                          |
| Deploy   | Vercel (web), Render (api)                                         |

---

## Repository layout

```
vayu-console/
├── apps/
│   ├── api/                 FastAPI backend
│   │   ├── app/
│   │   │   ├── api/         Routers, routes, shared dependencies
│   │   │   ├── core/        Config, logging, middleware
│   │   │   ├── database/    Engine, sessions, declarative base
│   │   │   ├── models/      SQLAlchemy models (empty in Phase 0)
│   │   │   ├── repositories/ Data access (empty in Phase 0)
│   │   │   ├── schemas/     Pydantic request/response schemas
│   │   │   ├── services/    Business logic
│   │   │   ├── utils/       Shared helpers
│   │   │   └── main.py      App factory and entrypoint
│   │   ├── alembic/         Migrations
│   │   └── tests/
│   └── web/                 Next.js frontend
│       └── src/
│           ├── app/         App Router pages
│           ├── components/  React components (ui/ = shadcn primitives)
│           └── lib/         API client, env, utilities
├── packages/
│   └── shared/              Types shared by web and api
├── docs/
│   ├── architecture/        Architecture decision records
│   ├── api/                 API documentation
│   ├── research/            Domain and data-source research
│   ├── architecture.md
│   ├── development.md
│   └── deployment.md
├── infra/                   Infrastructure notes and config
├── scripts/                 Repository tooling
└── .github/workflows/       CI
```

---

## Local setup

**Prerequisites:** Node.js 20+, Python 3.12+, git.

```bash
git clone https://github.com/Pranavsingh431/vayu_console.git
cd vayu_console

# Frontend + shared packages (npm workspaces, install from the root)
npm install

# Backend
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ../..

# Environment (optional for Phase 0 — see below)
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local

# Enable the pre-commit secret check (recommended: this repo is public)
git config core.hooksPath .githooks
```

No configuration is required to run Phase 0. `DATABASE_URL` and the API keys can stay
empty; `/health` reports them as `not_configured` rather than failing.

### Run

Two terminals:

```bash
npm run dev:api     # http://localhost:8000
npm run dev:web     # http://localhost:3000
```

| URL                           | What                                    |
| ----------------------------- | --------------------------------------- |
| http://localhost:3000         | Landing page                            |
| http://localhost:3000/status  | Status page (calls the API's `/health`) |
| http://localhost:8000/health  | Liveness + dependency status            |
| http://localhost:8000/version | Build identity                          |
| http://localhost:8000/docs    | OpenAPI docs (non-production only)      |

### Checks

These are exactly what CI runs:

```bash
# Frontend
npm run format:check
npm run lint
npm run typecheck
npm run build

# Backend
cd apps/api
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/mypy app tests
.venv/bin/pytest
```

More detail in [docs/development.md](docs/development.md).

---

## Environment variables

Full reference with links to each provider: [`.env.example`](.env.example) and
[`apps/web/.env.example`](apps/web/.env.example).

| Variable                            | Required                             | Purpose                                    |
| ----------------------------------- | ------------------------------------ | ------------------------------------------ |
| `ENVIRONMENT`                       | no (default `development`)           | `development` \| `staging` \| `production` |
| `DATABASE_URL`                      | **in production**                    | Supabase PostgreSQL connection string      |
| `CORS_ORIGINS`                      | in production                        | Comma-separated allowed browser origins    |
| `SUPABASE_URL`                      | later phases                         | Supabase project URL                       |
| `SUPABASE_ANON_KEY`                 | later phases                         | Public Supabase key                        |
| `SUPABASE_SERVICE_ROLE_KEY`         | later phases                         | Server-only Supabase key                   |
| `REDIS_URL`                         | later phases                         | Cache connection                           |
| `OPENROUTER_API_KEY`                | later phases                         | LLM access                                 |
| `DATA_GOV_API_KEY`                  | later phases                         | CPCB ground stations via data.gov.in       |
| `NASA_FIRMS_API_KEY`                | later phases                         | FIRMS active fire data                     |
| `NASA_EARTHDATA_BEARER_TOKEN`       | later phases                         | NASA Earthdata products                    |
| `COPERNICUS_USERNAME` / `_PASSWORD` | later phases                         | Copernicus Data Space (OAuth 2.0)          |
| `NEXT_PUBLIC_API_BASE_URL`          | no (default `http://localhost:8000`) | API base URL for the browser               |

`.env` is gitignored and must never be committed. `scripts/check-secrets.sh` runs in CI
to enforce that.

---

## Deployment

- **Frontend → Vercel**, root directory `apps/web`.
- **Backend → Render**, via the [`render.yaml`](render.yaml) blueprint.

Step-by-step: [docs/deployment.md](docs/deployment.md).

---

## License

[MIT](LICENSE)
