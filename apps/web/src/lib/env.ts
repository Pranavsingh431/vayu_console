/**
 * Client-visible environment configuration.
 *
 * `NEXT_PUBLIC_*` values are inlined into the browser bundle at build time, so
 * they must be referenced as full literals (`process.env.NEXT_PUBLIC_API_BASE_URL`)
 * rather than looked up dynamically — Next cannot substitute what it cannot see.
 */

function readApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  // A trailing slash here produces `//health` once paths are joined.
  return value.replace(/\/+$/, "");
}

export const env = {
  /** Base URL of the Vayu Console API, without a trailing slash. */
  apiBaseUrl: readApiBaseUrl(),
} as const;
