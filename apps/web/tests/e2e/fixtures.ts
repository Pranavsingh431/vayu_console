import type { Page, Route } from "@playwright/test";

import decisionExample from "./fixtures/decision-example.json";
import evidenceExample from "./fixtures/evidence-example.json";
import stations from "./fixtures/stations.json";

/**
 * Network mocking for E2E.
 *
 * The fixtures are **real captured responses** from the deployed API, not
 * hand-written shapes. A hand-written mock drifts from the server and the suite
 * ends up testing a fiction — passing green while production is broken. Refresh
 * them with:
 *
 *   curl https://vayu-console-api.onrender.com/evidence/example \
 *     -o apps/web/tests/e2e/fixtures/evidence-example.json
 *
 * Mocking at the network boundary (rather than stubbing modules) means the real
 * fetch, the real error classes and the real TanStack cache all run. Only the
 * server is absent.
 */

export const API = "http://127.0.0.1:8199";

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    contentType: "application/json",
    headers: { "access-control-allow-origin": "*" },
    body: JSON.stringify(body),
  });

/** The happy path: every endpoint the console calls, answered. */
export async function mockApi(page: Page) {
  await page.route(`${API}/evidence/example`, (r) => json(r, evidenceExample));
  await page.route(`${API}/decision/example`, (r) => json(r, decisionExample));
  await page.route(`${API}/stations**`, (r) => json(r, stations));
  await page.route(`${API}/evidence/evaluate`, (r) => json(r, evidenceExample));
  await page.route(`${API}/decision/evaluate`, (r) => json(r, decisionExample));
}

/** Total network failure — the state a judge hits if Render is asleep. */
export async function mockApiDown(page: Page) {
  await page.route(`${API}/**`, (r) => r.abort("failed"));
}

/**
 * The station list is empty: the scenario names an instant nothing reported at.
 * Distinct from the API being down, and the console must not conflate them.
 */
export async function mockNoStations(page: Page) {
  await page.route(`${API}/evidence/example`, (r) => json(r, evidenceExample));
  await page.route(`${API}/decision/example`, (r) => json(r, decisionExample));
  await page.route(`${API}/stations**`, (r) => json(r, []));
}

/**
 * Every hypothesis unjudgeable. The console must say "we cannot see" rather than
 * rendering a clean bill of health — the single most important failure mode in
 * the product.
 */
export async function mockInsufficientEvidence(page: Page) {
  const blind = {
    ...evidenceExample,
    measured_pm25: null,
    overall_quality: "no_data",
    summary:
      "No hypothesis could be judged at this station-hour: the required observations are missing. This is not evidence that the air is clean.",
    evidence: evidenceExample.evidence.map((e) => ({
      ...e,
      status: "insufficient_evidence",
      strength: "insufficient_evidence",
      evidence_quality: "no_data",
      likelihood_ratio: null,
      stars: "—",
      supporting_observations: [],
    })),
  };
  const noAction = {
    ...decisionExample,
    overall_status: "insufficient_evidence",
    recommendations: [],
    data_quality: "no_data",
    requires_human_review: true,
    summary:
      "No recommendation can be justified: the observations required to judge any hypothesis are missing. This is not evidence that the air is clean, or that no action is needed — it means the system cannot see.",
  };

  await page.route(`${API}/evidence/example`, (r) => json(r, blind));
  await page.route(`${API}/decision/example`, (r) => json(r, noAction));
  await page.route(`${API}/stations**`, (r) => json(r, stations));
  await page.route(`${API}/evidence/evaluate`, (r) => json(r, blind));
  await page.route(`${API}/decision/evaluate`, (r) => json(r, noAction));
}

/** Fail the console's test run on any browser console error. */
export function trackConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}
