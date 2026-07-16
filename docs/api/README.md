# API Documentation

The API is self-documenting via OpenAPI. With the backend running:

- Swagger UI — http://localhost:8000/docs
- ReDoc — http://localhost:8000/redoc
- Raw schema — http://localhost:8000/openapi.json

These are disabled in production.

## Endpoints (Phase 0)

| Method | Path       | Purpose                               |
| ------ | ---------- | ------------------------------------- |
| GET    | `/health`  | Liveness and dependency status        |
| GET    | `/version` | Build identity: name, version, commit |

### `GET /health`

Returns 200 whenever the process is alive — it is a liveness probe, and Render recycles a
service that fails it. Read `status` to tell healthy from degraded.

```json
{
  "status": "ok",
  "environment": "development",
  "version": "0.1.0",
  "checks": {
    "database": {
      "status": "not_configured",
      "detail": "DATABASE_URL is not set.",
      "latency_ms": null
    }
  }
}
```

`status`: `ok` | `degraded` — degraded means a dependency is `unavailable`.
`checks.*.status`: `ok` | `unavailable` | `not_configured`.

### `GET /version`

```json
{ "name": "Vayu Console API", "version": "0.1.0", "environment": "production", "commit": "a1b2c3d" }
```

`commit` is null locally; on Render it is the deployed SHA.

## Conventions

- Every response carries `X-Request-ID`, echoing the request's if supplied. Quote it in a
  bug report and the matching log line can be found.
- Feature endpoints are versioned under `/api/v1`. `/health` and `/version` are not — they
  describe the deployment, not the product, and must stay stable.

_(Phase 1+)_ Endpoint reference as the surface grows.
