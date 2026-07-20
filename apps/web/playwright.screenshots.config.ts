import { defineConfig, devices } from "@playwright/test";

/**
 * Submission screenshot capture.
 *
 * Separate from `playwright.config.ts` on purpose: this run writes PNGs into
 * `docs/assets/screenshots/`, and the E2E suite must stay side-effect free so it
 * can run on CI without dirtying the tree.
 *
 *   npm run screenshots
 *
 * Single project, one viewport: the images go in a README side by side, and a
 * mix of 1920 and 1440 captures reads as inconsistent rather than thorough.
 */
export default defineConfig({
  testDir: "./tests",
  testMatch: "screenshots.spec.ts",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],

  use: {
    // Device preset first: it carries its own viewport, and spreading it after
    // the override silently discards the size we actually want.
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:3100",
    viewport: { width: 1440, height: 900 },
    // Retina, so the images stay sharp when a judge zooms a README on a good
    // display. Halves again cleanly if they need to be smaller.
    deviceScaleFactor: 2,
  },

  webServer: {
    command: "npm run build && npm run start -- --port 3100",
    url: "http://127.0.0.1:3100/console",
    reuseExistingServer: true,
    timeout: 180_000,
    env: { NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8199" },
  },
});
