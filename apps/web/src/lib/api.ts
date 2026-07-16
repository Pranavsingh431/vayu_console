/**
 * Typed client for the Vayu Console API.
 *
 * The only place `fetch` is called against the backend. Every response is typed
 * from `@vayu/shared`, so a change to an API schema surfaces as a type error
 * here rather than as undefined at runtime.
 */

import type { HealthResponse, VersionResponse } from "@vayu/shared";

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
};

/** Query keys for TanStack Query, kept in one place to avoid typos. */
export const queryKeys = {
  health: ["health"] as const,
  version: ["version"] as const,
};
