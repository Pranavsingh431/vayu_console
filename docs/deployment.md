# Deployment

> **Status:** Phase 0. The pipeline is prepared and the apps are deploy-ready. Sections
> marked _(Phase N)_ are placeholders.

Frontend → **Vercel**. Backend → **Render**. Database → **Supabase**.

Deploy the backend first: the frontend needs its URL, and the backend needs the
frontend's URL for CORS. That circularity is resolved in step 4.

---

## 1. Database (Supabase)

1. Create a project at [supabase.com](https://supabase.com). Choose a region close to
   Delhi — Mumbai (`ap-south-1`) is nearest, then Singapore (`ap-southeast-1`).
   The region is fixed at creation and cannot be changed later.

2. **Use the connection pooler URI, not the direct connection.** This is the single
   most important step, and getting it wrong produces a confusing failure.

   Supabase offers two kinds of host:

   | Kind      | Host                                 | Resolves to   | Works on Render? |
   | --------- | ------------------------------------ | ------------- | ---------------- |
   | Direct    | `db.[ref].supabase.co`               | **IPv6 only** | ❌ No            |
   | Supavisor | `aws-0-[region].pooler.supabase.com` | IPv4 (+IPv6)  | ✅ Yes           |

   The direct host publishes **no A record at all**. Render's outbound network is
   IPv4-only, so it cannot reach it — the failure looks like this, and names an IPv6
   address rather than saying anything about IPv6:

   ```
   connection to server at "2406:da14:...", port 5432 failed: Network is unreachable
   ```

   In the dashboard press **Connect** (top bar) and copy the **Session pooler** URI.
   Note that the username changes to `postgres.[ref]`, not plain `postgres`:

   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
   ```

   Use **session mode (5432)**: this API is a long-lived server, and Alembic needs
   session mode for migrations. Transaction mode (6543) is for serverless functions
   and breaks psycopg's prepared statements unless you disable them.

3. Substitute your real password for `[password]`. If it contains URL-unsafe characters
   (`@ : / ? # &`), percent-encode them or the URL will not parse.
4. **Project Settings → API** — copy `SUPABASE_URL`, the `anon` key, and the
   `service_role` key.

> The `service_role` key bypasses row-level security. It belongs on the server only. Never
> give it a `NEXT_PUBLIC_` prefix.

_(Phase 1)_ Enable the PostGIS extension and run migrations. Phase 0 creates no tables.

---

## 2. Backend (Render)

The [`render.yaml`](../render.yaml) blueprint at the repository root declares the service.

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**.
2. Connect `Pranavsingh431/vayu_console`. Render reads `render.yaml` and proposes
   **vayu-console-api**.
3. Render prompts for every variable marked `sync: false`. At minimum:

   | Variable       | Value                                                                                                                                                    |
   | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | `DATABASE_URL` | The Supabase URI from step 1.                                                                                                                            |
   | `CORS_ORIGINS` | **Must not be blank.** Use `http://localhost:3000` as a placeholder, then replace with the Vercel URL in step 4. The service refuses to boot without it. |

   The rest (Supabase keys, `REDIS_URL`, data-source keys) are unused in Phase 0 and may
   be left blank.

4. **Apply.** First build takes a few minutes.

The blueprint pins `ENVIRONMENT=production`, which makes configuration validation
strict: **a missing `DATABASE_URL` or a blank `CORS_ORIGINS` will stop the service from
booting.** Both are deliberate. A blank `CORS_ORIGINS` used to be accepted, and it
silently disabled CORS entirely — `/health` returned 200 to curl with `database: ok`
while every browser request was blocked and the console rendered blank. An API that
looks healthy and serves nobody is the worst of both worlds, so it now fails at boot.

If a deploy fails immediately, read the boot log — the error names the missing variable.

Verify:

```bash
curl https://vayu-console-api.onrender.com/health
curl https://vayu-console-api.onrender.com/version
```

`/version` reports the deployed commit: Render injects `RENDER_GIT_COMMIT` and the app
reads it automatically.

**Free plan:** the service sleeps after ~15 minutes idle, and the next request pays a
30–60s cold start. Fine for judging; upgrade if you need it warm during a live demo.

---

## 3. Frontend (Vercel)

1. [vercel.com/new](https://vercel.com/new) → import `Pranavsingh431/vayu_console`.
2. **Set Root Directory to `apps/web`.** This is the one setting that matters. Vercel then
   detects Next.js and installs from the root lockfile, hoisting the workspace correctly.
3. Framework preset: **Next.js** (auto-detected). Leave build and output settings alone.
4. Environment variables:

   | Variable                   | Value                                   |
   | -------------------------- | --------------------------------------- |
   | `NEXT_PUBLIC_API_BASE_URL` | `https://vayu-console-api.onrender.com` |

   No trailing slash. Set it for Production, Preview, and Development.

5. **Deploy.**

> `NEXT_PUBLIC_*` values are inlined into the browser bundle at build time. Changing one
> requires a **redeploy** — restarting is not enough. And never put a secret behind that
> prefix: it ships to every visitor.

---

## 4. Close the CORS loop

Vercel has now given you a URL. The API must be told to accept it.

1. Render → **vayu-console-api → Environment**.
2. Set `CORS_ORIGINS` to your Vercel production URL, comma-separated if more than one:

   ```
   https://vayu-console.vercel.app
   ```

3. Save. Render redeploys.

Vercel preview deployments get a unique URL per commit, so they will be blocked by CORS
unless you add them. That is expected; add specific preview URLs as needed rather than
allowing a wildcard.

Verify end to end: open `https://<your-app>.vercel.app/status`. It should report the API as
operational. A browser console CORS error here means step 2 has not taken effect yet.

---

## 5. CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every push and pull
request against `main`:

| Job         | Checks                                       |
| ----------- | -------------------------------------------- |
| API         | ruff, black, mypy, pytest                    |
| Web         | prettier, eslint, tsc, next build            |
| Secret scan | no environment file or credential is tracked |

Any failure fails the workflow. CI does not deploy — Vercel and Render each watch the
repository and deploy on push to `main` themselves.

---

## Environment variables by surface

| Variable                            |   Render (api)    | Vercel (web) | Required                       |
| ----------------------------------- | :---------------: | :----------: | ------------------------------ |
| `ENVIRONMENT`                       | ✅ (`production`) |      —       | set by blueprint               |
| `DATABASE_URL`                      |        ✅         |      —       | **yes, in production**         |
| `CORS_ORIGINS`                      |        ✅         |      —       | yes, or the browser is blocked |
| `LOG_LEVEL` / `LOG_FORMAT`          |        ✅         |      —       | set by blueprint               |
| `SUPABASE_URL`                      |        ✅         |      —       | later phases                   |
| `SUPABASE_ANON_KEY`                 |        ✅         |      —       | later phases                   |
| `SUPABASE_SERVICE_ROLE_KEY`         |        ✅         |      —       | later phases — server only     |
| `REDIS_URL`                         |        ✅         |      —       | later phases                   |
| `OPENROUTER_API_KEY`                |        ✅         |      —       | later phases                   |
| `DATA_GOV_API_KEY`                  |        ✅         |      —       | later phases                   |
| `NASA_FIRMS_API_KEY`                |        ✅         |      —       | later phases                   |
| `NASA_EARTHDATA_BEARER_TOKEN`       |        ✅         |      —       | later phases — expires         |
| `COPERNICUS_USERNAME` / `_PASSWORD` |        ✅         |      —       | later phases                   |
| `NEXT_PUBLIC_API_BASE_URL`          |         —         |      ✅      | yes                            |

---

## Rollback

**Render:** service → **Events** → pick the last good deploy → **Rollback**.
**Vercel:** project → **Deployments** → pick the last good one → **Promote to Production**.

Confirm with `/version`, which reports the running commit.

---

## Troubleshooting

| Symptom                                              | Cause and fix                                                                                                                                   |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `Network is unreachable`, host looks like `2406:...` | You used the **direct** connection host, which is IPv6-only. Render is IPv4-only. Switch `DATABASE_URL` to the Session pooler URI (see step 2). |
| `Tenant or user not found`                           | The pooler host's region does not match the project's, or the username is missing the `postgres.[ref]` suffix.                                  |
| Render: service exits at boot                        | A required variable is missing. The log names it — usually `DATABASE_URL`.                                                                      |
| `/health` → `database: unavailable`                  | `DATABASE_URL` is wrong or Supabase is unreachable. Check the password is percent-encoded.                                                      |
| `/health` → `database: not_configured`               | `DATABASE_URL` is blank. Blank counts as unset.                                                                                                 |
| CORS error in the browser                            | The Vercel URL is not in `CORS_ORIGINS`. Trailing slashes matter.                                                                               |
| Status page shows `localhost:8000` in production     | `NEXT_PUBLIC_API_BASE_URL` was not set at build time. Redeploy after setting it.                                                                |
| First request takes 60s                              | Free-plan cold start. Expected.                                                                                                                 |
| Vercel build: cannot resolve `@vayu/shared`          | Root Directory is not `apps/web`, so the workspace was not hoisted.                                                                             |

_(Later phase)_ Staging environment, migration-on-deploy, uptime monitoring.
