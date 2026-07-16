/**
 * System endpoint contracts.
 *
 * Mirrors `apps/api/app/schemas/health.py`.
 */

/** Status of a single dependency the API relies on. */
export type ComponentStatus = "ok" | "unavailable" | "not_configured";

/** Overall service status. `degraded` means alive but a dependency is down. */
export type ServiceStatus = "ok" | "degraded";

/** Health of one dependency. */
export interface ComponentHealth {
  status: ComponentStatus;
  /** Human-readable context, e.g. why a probe failed. */
  detail: string | null;
  /** Probe duration in milliseconds, or null when no probe ran. */
  latency_ms: number | null;
}

/** Response body of `GET /health`. */
export interface HealthResponse {
  status: ServiceStatus;
  environment: string;
  version: string;
  checks: Record<string, ComponentHealth>;
}

/** Response body of `GET /version`. */
export interface VersionResponse {
  name: string;
  version: string;
  environment: string;
  /** Deployed git SHA; null when running locally. */
  commit: string | null;
}
