/**
 * Typed client for the Vayu Console API.
 *
 * The only place `fetch` is called against the backend. Every response is typed
 * from `@vayu/shared`, so a change to an API schema surfaces as a type error
 * here rather than as undefined at runtime.
 */

import type { DecisionReport, EvidenceReport, HealthResponse, VersionResponse } from "@vayu/shared";

import { env } from "./env";

/** An API call that reached the server but returned a non-2xx status. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** An API call that never reached the server (offline, DNS, CORS, timeout). */
export class ApiUnreachableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiUnreachableError";
  }
}

const REQUEST_TIMEOUT_MS = 10_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${env.apiBaseUrl}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      // The status page must reflect the backend now, not when it was built.
      cache: "no-store",
    });
  } catch (cause) {
    // Distinguished from ApiError so the UI can say "cannot reach" rather than
    // reporting a status code that never existed.
    throw new ApiUnreachableError(
      cause instanceof Error && cause.name === "TimeoutError"
        ? `Request to ${url} timed out after ${REQUEST_TIMEOUT_MS}ms.`
        : `Could not reach ${url}. Is the API running?`,
    );
  }

  if (!response.ok) {
    throw new ApiError(`${response.status} ${response.statusText}`, response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  version: () => request<VersionResponse>("/version"),

  /** The worked Diwali 2019 example. Needs no database, so the demo always loads. */
  evidenceExample: () => request<EvidenceReport>("/evidence/example"),
  decisionExample: () => request<DecisionReport>("/decision/example"),

  /** Live evidence for a station-hour. */
  evidence: (stationId: number, at: string) =>
    request<EvidenceReport>("/evidence/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ station_id: stationId, at }),
    }),

  /** Recommendations from an evidence report. The decision engine reads nothing else. */
  decision: (report: EvidenceReport) =>
    request<DecisionReport>("/decision/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    }),

  stations: (at?: string) =>
    request<StationSummary[]>(`/stations${at ? `?at=${encodeURIComponent(at)}` : ""}`),

  /**
   * Evidence for a scenario instant, against real ingested data.
   *
   * A scenario names a moment, not a station, so this resolves one: ask which
   * stations were actually reporting then, and take the first. Picking a station
   * that was offline would render "insufficient evidence" everywhere and read as
   * a broken demo rather than an honest one.
   */
  evidenceForScenario: async (at: string): Promise<EvidenceReport> => {
    const stations = await api.stations(at);
    if (!stations.length) {
      throw new ApiError(`No station was reporting at ${at}.`, 404);
    }
    return api.evidence(stations[0].id, at);
  },
};

/** A station, for the map. */
export interface StationSummary {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  provider: string | null;
}

/** Query keys for TanStack Query, kept in one place to avoid typos. */
export const queryKeys = {
  health: ["health"] as const,
  version: ["version"] as const,
  stations: ["stations"] as const,
  evidenceExample: ["evidence", "example"] as const,
  decisionExample: ["decision", "example"] as const,
  evidence: (stationId: number, at: string) => ["evidence", stationId, at] as const,
  decision: (stationId: number, at: string) => ["decision", stationId, at] as const,
  scenarioEvidence: (id: string, at: string, isExample: boolean) =>
    ["scenario", "evidence", id, at, isExample] as const,
  scenarioDecision: (id: string, at: string, isExample: boolean) =>
    ["scenario", "decision", id, at, isExample] as const,
};
