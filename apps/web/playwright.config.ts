import { defineConfig, devices } from "@playwright/test";

/**
 * E2E configuration.
 *
 * The API is mocked at the network boundary by default (see `tests/e2e/fixtures.ts`).
 * These tests must pass on a laptop with no database, on CI with no secrets, and
 * without waking a sleeping Render instance — a suite that needs live
 * infrastructure is a suite nobody runs, and an unrun suite protects nothing.
 *
 * Set `E2E_LIVE_API=1` to run against a real backend instead.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],

  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      // 16:9 desktop is the stated primary target and the demo surface.
      name: "desktop-16x9",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 } },
    },
    {
      // The realistic worst case a judge might open it on.
      name: "laptop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],

  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        // Production build, not dev: dev-only overlays and Fast Refresh are not
        // what a judge sees, and a corrupted .next dev cache once made the
        // console render a permanent skeleton while the API returned 200s.
        command: "npm run build && npm run start -- --port 3100",
        url: "http://127.0.0.1:3100/console",
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        env: { NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8199" },
      },
});
