# Architecture

> **Status:** Phase 0. Sections marked _(Phase N)_ are placeholders to be filled as the
> corresponding work lands. What is written here without that marker is implemented today.

---

## 1. Purpose and constraints

Vayu Console is a decision-support tool for municipal officers, not a consumer AQI app.
That single distinction drives most of the design:

- **Every output must be explainable.** An officer has to justify an intervention. A number
  with no evidence chain is not usable, so the system carries provenance alongside values.
- **Physically grounded inference over black-box prediction.** Source attribution is argued
  from meteorology, fire activity, and station chemistry — not asserted by a model.
- **Delhi only.** No multi-city abstraction in this sprint. Generalising early would cost
  time and buy nothing.

## 2. System context

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  apps/web    │  HTTPS  │  apps/api    │         │   Supabase   │
│  Next.js 15  ├────────►│   FastAPI    ├────────►│  PostgreSQL  │
│  (Vercel)    │  JSON   │  (Render)    │  SQL    │  + PostGIS   │
└──────────────┘         └──────┬───────┘         └──────────────┘
                                │
                                ▼
                    external data sources (later phases)
                    CPCB · NASA FIRMS · Earthdata · Copernicus · Open-Meteo
```

The browser never talks to an external data source or to Supabase directly. The API is the
only trust boundary that holds credentials.

## 3. Backend layering

Requests flow in one direction; each layer may only call the one beneath it.

| Layer            | Directory                     | Responsibility                                         |
| ---------------- | ----------------------------- | ------------------------------------------------------ |
| Routes           | `app/api/routes/`             | HTTP shape only: parse, delegate, serialise.           |
| Dependencies     | `app/api/deps.py`             | Construct services; the seam tests override.           |
| Services         | `app/services/`               | Business logic. No HTTP, no raw SQL.                   |
| Repositories     | `app/repositories/`           | All database queries. The only place SQLAlchemy lives. |
| Models / Schemas | `app/models/`, `app/schemas/` | Persistence and wire shapes, kept separate.            |

**Why separate `models` from `schemas`:** the shape stored is not the shape served.
Coupling them means a column rename becomes an API break.

### Configuration

`app/core/config.py` — Pydantic Settings, validated once and cached.

Validation is deliberately asymmetric:

- **Production** requires every operationally necessary variable and refuses to boot
  otherwise. A misconfigured deploy should fail at startup, loudly, not serve wrong
  answers under load.
- **Development** treats them as optional so a fresh clone runs with zero setup.
  `/health` reports what is unconfigured.

Blank and absent are treated identically (`DATABASE_URL=` means unset), because both
Render and Vercel let you declare a variable with an empty value.

### Logging

`app/core/logging.py` emits one JSON object per line in deployed environments.
`RequestLoggingMiddleware` logs timestamp, endpoint, latency, and status code for every
request, plus an `X-Request-ID` correlation id echoed to the client — so a user-reported
error maps to a specific log line.

## 4. Frontend structure

- `src/app/` — App Router pages. Server Components by default.
- `src/components/ui/` — shadcn/ui primitives. Owned by the repo, edited freely.
- `src/lib/api.ts` — the only place the backend is fetched. Distinguishes
  `ApiError` (server responded, non-2xx) from `ApiUnreachableError` (never arrived), because
  the UI should say different things in those cases.
- TanStack Query owns server state. The `QueryClient` is created per-request inside
  `useState` — a module-level client would leak one user's cache into another's response.

## 5. Shared contracts

`packages/shared` holds the TypeScript mirror of the API's Pydantic schemas. It is imported
by the web app and type-checked in CI, so an API change that the frontend has not accounted
for fails the build rather than reaching production.

_(Later phase: generate these from the OpenAPI schema instead of hand-mirroring, once the
surface is large enough to justify the tooling.)_

## 6. Data model

_(Phase 1)_ No application tables exist. Alembic is configured with a baseline revision
carrying no schema, so the first real migration has a parent.

PostGIS is part of the stack for spatial queries (hotspot clustering, station catchments,
fire proximity). The Alembic environment already filters PostGIS- and Supabase-owned tables
out of autogenerate diffs, which otherwise proposes dropping them.

## 7. Data sources

_(Phase 1)_ To be filled in as each integration lands.

| Source                | Purpose                         | Auth                        |
| --------------------- | ------------------------------- | --------------------------- |
| CPCB / data.gov.in    | Ground station measurements     | API key                     |
| NASA FIRMS            | Active fire / thermal anomalies | Map key (5000 req / 10 min) |
| NASA Earthdata        | Satellite products              | Bearer token (expires)      |
| Copernicus Data Space | Sentinel products               | OAuth 2.0 token exchange    |
| Open-Meteo            | Weather                         | None                        |

## 8. Caching

_(Phase 2)_ Redis is in the architecture and has a config slot, but is not connected.
Upstream rate limits (notably FIRMS) make caching a correctness concern, not just a
performance one.

## 9. Source attribution

_(Phase 3)_

## 10. Recommendation engine

_(Phase 4)_

## 11. Security

- Credentials live only in the API process. Nothing sensitive is exposed to the browser;
  a `NEXT_PUBLIC_` prefix ships to every visitor and is never used for a secret.
- `.env` is gitignored, and `scripts/check-secrets.sh` fails CI if an environment file or
  a credential pattern is ever tracked.
- OpenAPI docs are disabled in production.
- Authentication is out of scope for this sprint _(later phase)_.

## 12. Decision log

Architecture decision records live in `docs/architecture/`.

| Decision                            | Rationale                                                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| psycopg3 over asyncpg               | Accepts libpq query params such as `sslmode=require`, which Supabase URLs carry, and drives both the app and Alembic.     |
| Async SQLAlchemy from the start     | The workload is I/O-bound against slow external APIs; retrofitting async later is invasive.                               |
| `/health` returns 200 when degraded | It is a liveness probe. Failing it would make Render recycle a healthy process because a dependency blinked.              |
| Next.js 15, not 16                  | shadcn/ui, deck.gl and MapLibre are best-tested against 15; a time-boxed sprint is the wrong place to absorb a new major. |
| Monorepo, npm workspaces            | One install, one lockfile, shared types without a publish step.                                                           |
