import { expect, test } from "@playwright/test";

import { mockApi, mockInsufficientEvidence } from "./e2e/fixtures";

/**
 * Submission screenshots, captured from the real application.
 *
 * Not a test suite — a capture script that happens to run on Playwright, so the
 * images in `docs/assets/screenshots/` are always the product as it actually
 * renders rather than a mockup that drifts from it.
 *
 *   npm run screenshots
 *
 * Driven by `playwright.screenshots.config.ts`, not the E2E config: this run
 * writes files, and a check suite should not have side effects.
 */

const DIR = "../../docs/assets/screenshots";

test.use({ viewport: { width: 1440, height: 900 } });

test("landing page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Open Operations Console" })).toBeVisible();
  await page.screenshot({ path: `${DIR}/01-landing.png` });
});

test("operations console — Diwali 2019", async ({ page }) => {
  await mockApi(page);
  await page.goto("/console");
  await expect(page.getByText("Severe")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Historical validation" })).toBeVisible();
  await page.screenshot({ path: `${DIR}/02-console-diwali.png` });
});

test("challenge recommendation modal", async ({ page }) => {
  await mockApi(page);
  await page.goto("/console");
  await page.getByRole("button", { name: "Why?" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.screenshot({ path: `${DIR}/03-challenge-modal.png` });
});

test("presentation mode mid-sequence", async ({ page }) => {
  await mockApi(page);
  await page.goto("/console");
  await page.getByRole("button", { name: "Present Incident" }).click();
  // Far enough in that evidence has been revealed but the tour is still running.
  await expect(page.getByRole("progressbar")).toBeVisible();
  await page.waitForTimeout(11_000);
  await page.screenshot({ path: `${DIR}/04-presentation-mode.png` });
  await page.keyboard.press("Escape");
});

test("insufficient evidence", async ({ page }) => {
  await mockInsufficientEvidence(page);
  await page.goto("/console");
  await expect(page.getByText("Insufficient evidence").first()).toBeVisible();
  await page.screenshot({ path: `${DIR}/05-insufficient-evidence.png` });
});

test("historical validation timeline", async ({ page }) => {
  await mockApi(page);
  await page.goto("/console");
  const timeline = page.getByRole("heading", { name: "Historical validation" });
  await expect(timeline).toBeVisible();
  // The timeline panel only, cropped from the console it lives in.
  const panel = page.locator("section").filter({ has: timeline });
  await panel.screenshot({ path: `${DIR}/06-validation-timeline.png` });
});
