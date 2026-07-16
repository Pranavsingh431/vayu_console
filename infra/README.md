# Infrastructure

Deployment topology and the reasoning behind it. Operational runbooks live in
[../docs/deployment.md](../docs/deployment.md).

| Component | Provider | Config                                  |
| --------- | -------- | --------------------------------------- |
| Web       | Vercel   | Dashboard; Root Directory = `apps/web`. |
| API       | Render   | [`render.yaml`](../render.yaml)         |
| Database  | Supabase | Dashboard                               |
| Cache     | Redis    | Not provisioned _(later phase)_         |

Only Render is declared as code today. Vercel and Supabase are dashboard-configured, which
is the pragmatic choice at this size — revisit if the setup ever needs to be reproducible
from scratch.

_(Later phase)_ Redis provisioning, staging environment, monitoring and alerting.
