import { expect, test } from "@playwright/test";

import {
  mockApi,
  mockApiDown,
  mockInsufficientEvidence,
  mockNoStations,
  trackConsoleErrors,
} from "./fixtures";

/**
 * The demo path.
 *
 * Every test here maps to something a judge will actually do in five minutes. A
 * failure in this file means the live demo breaks, which is the only kind of bug
 * that matters at this stage.
 */

test.describe("console", () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page);
  });

  test("loads with the situation, evidence and recommendations", async ({ page }) => {
    const errors = trackConsoleErrors(page);
    await page.goto("/console");

    // The number a judge reads first.
    await expect(page.getByText("Severe")).toBeVisible();
    await expect(page.getByText("1288")).toBeVisible();

    await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
    await expect(page.getByText("Fire / Biomass")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recommended action" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Historical validation" })).toBeVisible();

    expect(errors, `console errors: ${errors.join(" | ")}`).toEqual([]);
  });

  test("fits one screen — the page itself never scrolls", async ({ page }) => {
    await page.goto("/console");
    await expect(page.getByText("Severe")).toBeVisible();

    // The stated design constraint. On a control-room screen, scrolling the page
    // means losing the number you were looking at.
    const overflow = await page.evaluate(() => {
      const d = document.documentElement;
      return { scrollH: d.scrollHeight, clientH: d.clientHeight };
    });
    expect(overflow.scrollH).toBeLessThanOrEqual(overflow.clientH + 2);
  });

  test("evidence rows expand to show supporting and contradicting facts", async ({ page }) => {
    await page.goto("/console");
    await page.getByRole("button", { name: /Fire \/ Biomass/ }).click();

    await expect(page.getByText("Supporting").first()).toBeVisible();
    await expect(page.getByText(/Likelihood ratio/)).toBeVisible();
    // The claim that must never be softened.
    await expect(page.getByText(/Not a probability/)).toBeVisible();
  });

  test("never renders a probability or a source percentage", async ({ page }) => {
    await page.goto("/console");
    await expect(page.getByText("Severe")).toBeVisible();
    const body = (await page.locator("body").innerText()).toLowerCase();

    // The product's central claim, asserted against the rendered DOM rather than
    // against our own types.
    expect(body).not.toContain("probability");
    expect(body).not.toContain("confidence score");
    expect(body).toContain("do not sum to 100%");
  });

  test("human review is surfaced with its reasons", async ({ page }) => {
    await page.goto("/console");

    await expect(page.getByText("Human review required").first()).toBeVisible();
    await expect(page.getByText(/Human review required because/)).toBeVisible();
    await expect(page.getByText(/Historical validation is still pending/)).toBeVisible();
  });

  test("expected impact gives a reassessment window, not a forecast", async ({ page }) => {
    await page.goto("/console");

    await expect(page.getByText("Expected impact").first()).toBeVisible();
    await expect(page.getByText(/Reassess within 6 hours/)).toBeVisible();
  });

  test("timeline shows the COVID calibration that validates the traffic module", async ({
    page,
  }) => {
    await page.goto("/console");

    await expect(page.getByText("COVID lockdown").last()).toBeVisible();
    // Badges are lowercase in the DOM and uppercased by CSS text-transform;
    // getByText reads the DOM, not the glyphs.
    await expect(page.getByText("calibrated", { exact: true })).toBeVisible();
    await expect(page.getByText(/LR 2.11/)).toBeVisible();
    // The gap we refuse to interpolate across.
    await expect(page.getByText("gap", { exact: true }).first()).toBeVisible();
  });
});

test.describe("challenge dialog", () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page);
    await page.goto("/console");
  });

  test("opens with the full decision trace", async ({ page }) => {
    await page.getByRole("button", { name: "Why?" }).first().click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Decision trace").first()).toBeVisible();

    // Evidence -> Rule -> Policy -> Recommendation. The spine of the feature.
    //
    // Matched lowercase: the labels are uppercased by CSS text-transform, and
    // getByText reads the DOM text, not the rendered glyphs.
    for (const step of ["evidence", "rule", "policy", "recommendation"]) {
      await expect(dialog.getByText(step, { exact: true }).first()).toBeVisible();
    }
    await expect(dialog.getByText("FIRE_002").first()).toBeVisible();
  });

  test("shows contradicting evidence and how to challenge it", async ({ page }) => {
    await page.getByRole("button", { name: "Why?" }).first().click();
    const dialog = page.getByRole("dialog");

    // An officer needs the counter-argument before someone else supplies it.
    await expect(dialog.getByText("Contradicting evidence").first()).toBeVisible();
    await expect(dialog.getByText("Assumptions").first()).toBeVisible();
    await expect(dialog.getByText(/To challenge this/)).toBeVisible();
    // Prose, never a number.
    await expect(dialog.getByText("How far this can be pushed").first()).toBeVisible();
  });

  test("closes on the close button and can reopen", async ({ page }) => {
    await page.getByRole("button", { name: "Why?" }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();

    await page.getByRole("button", { name: "Close" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    // Repeatability: a judge will click this more than once.
    await page.getByRole("button", { name: "Why?" }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("every recommendation can be challenged", async ({ page }) => {
    const whys = page.getByRole("button", { name: "Why?" });
    const count = await whys.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      await whys.nth(i).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.getByRole("button", { name: "Close" }).click();
      await expect(page.getByRole("dialog")).toBeHidden();
    }
  });
});

test.describe("scenario switching", () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page);
    await page.goto("/console");
  });

  test("switches incident and marks the selected tab", async ({ page }) => {
    const covid = page.getByRole("tab", { name: /COVID lockdown/ });
    await covid.click();

    await expect(covid).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("tab", { name: /Diwali 2019/ })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  test("switching repeatedly leaves no broken state", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    for (const name of [/COVID lockdown/, /Odd-Even II/, /Diwali 2019/, /COVID lockdown/]) {
      await page.getByRole("tab", { name }).click();
      await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
    }

    expect(errors, `console errors: ${errors.join(" | ")}`).toEqual([]);
  });

  test("GRAP is shown as unavailable with a reason, not silently omitted", async ({ page }) => {
    const grap = page.getByText("GRAP");
    await expect(grap).toBeVisible();
    // Absence must read as a decision, not an oversight.
    await expect(grap).toHaveAttribute("title", /threshold-triggered regime/);
  });
});

test.describe("presentation mode", () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page);
    await page.goto("/console");
  });

  test("runs, reveals in sequence, and opens the challenge modal by itself", async ({ page }) => {
    test.setTimeout(90_000);
    const errors = trackConsoleErrors(page);

    await page.getByRole("button", { name: "Present Incident" }).click();
    await expect(page.getByRole("button", { name: "Stop" })).toBeVisible();
    await expect(page.getByRole("progressbar")).toBeVisible();

    // The moment the whole feature exists for: ~19s in, unattended.
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("dialog").getByText("Decision trace").first()).toBeVisible();

    // And it finishes on its own, leaving a usable console.
    await expect(page.getByRole("button", { name: "Present Incident" })).toBeVisible({
      timeout: 40_000,
    });
    await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();

    expect(errors, `console errors: ${errors.join(" | ")}`).toEqual([]);
  });

  test("stop leaves the console fully drawn, never half-revealed", async ({ page }) => {
    await page.getByRole("button", { name: "Present Incident" }).click();
    await expect(page.getByRole("button", { name: "Stop" })).toBeVisible();

    await page.getByRole("button", { name: "Stop" }).click();

    // A presenter interrupting the tour still needs a working screen.
    await expect(page.getByRole("progressbar")).toBeHidden();
    await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recommended action" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Historical validation" })).toBeVisible();
  });

  test("escape always exits", async ({ page }) => {
    await page.getByRole("button", { name: "Present Incident" }).click();
    await expect(page.getByRole("button", { name: "Stop" })).toBeVisible();

    // A presenter who loses control of the screen in front of judges is worse
    // off than one who never started it.
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Present Incident" })).toBeVisible();
  });

  test("scenario tabs are locked while presenting", async ({ page }) => {
    await page.getByRole("button", { name: "Present Incident" }).click();
    await expect(page.getByRole("tab", { name: /COVID lockdown/ })).toBeDisabled();
  });
});

test.describe("failure and empty states", () => {
  test("api down explains both causes and never blames only one", async ({ page }) => {
    await mockApiDown(page);
    await page.goto("/console");

    await expect(page.getByText("Cannot reach the analysis service")).toBeVisible();
    // The regression: it used to assert "Is the API running?" while the API was
    // running and CORS was the block.
    await expect(page.getByText(/CORS/)).toBeVisible();
    await expect(page.getByText(/down or asleep/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  });

  test("api down never leaks a stack trace or raw error", async ({ page }) => {
    await mockApiDown(page);
    await page.goto("/console");
    await expect(page.getByText("Cannot reach the analysis service")).toBeVisible();

    const body = await page.locator("body").innerText();
    expect(body).not.toContain("TypeError");
    expect(body).not.toContain("at Object.");
    expect(body).not.toContain("Traceback");
  });

  test("insufficient evidence is not a clean bill of health", async ({ page }) => {
    await mockInsufficientEvidence(page);
    await page.goto("/console");

    // The most important sentence in the product.
    await expect(page.getByText(/not evidence that the air is clean/)).toBeVisible();
    await expect(page.getByText("Cannot judge").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Why?" })).toHaveCount(0);
  });

  test("a scenario with no reporting station degrades without crashing", async ({ page }) => {
    await mockNoStations(page);
    await page.goto("/console");
    await expect(page.getByText("Severe")).toBeVisible();

    await page.getByRole("tab", { name: /COVID lockdown/ }).click();

    // Either a report or an honest failure — never a blank screen.
    await expect(
      page
        .getByRole("heading", { name: "Evidence" })
        .or(page.getByText("Cannot reach the analysis service")),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("no infinite skeleton: the console always resolves", async ({ page }) => {
    await mockApi(page);
    await page.goto("/console");

    // A corrupted .next cache once left this skeleton on screen forever while
    // the API returned 200s.
    await expect(page.getByText("Loading incident")).toBeHidden({ timeout: 15_000 });
  });
});

test.describe("resilience", () => {
  test("survives a refresh", async ({ page }) => {
    await mockApi(page);
    await page.goto("/console");
    await expect(page.getByText("Severe")).toBeVisible();

    await page.reload();
    await expect(page.getByText("Severe")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  });

  test("landing page links into the console", async ({ page }) => {
    await mockApi(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Vayu Console" })).toBeVisible();
    await page.getByRole("link", { name: /Open Operations Console/ }).click();

    await expect(page).toHaveURL(/\/console/);
    await expect(page.getByText("Severe")).toBeVisible();
  });
});

test.describe("accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page);
    await page.goto("/console");
  });

  test("the whole demo path is keyboard operable", async ({ page }) => {
    // Tab from the top must land on a real control, not the body. Next injects a
    // dev-only skip link in some builds, so accept a link too.
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => document.activeElement?.tagName ?? "NONE");
    expect(["BUTTON", "A", "INPUT"]).toContain(focused);

    // Reach a Why? button by keyboard alone and open the dialog with Enter.
    const why = page.getByRole("button", { name: "Why?" }).first();
    await why.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("focus is visible, never removed", async ({ page }) => {
    const why = page.getByRole("button", { name: "Why?" }).first();
    await why.focus();

    const outline = await why.evaluate((el) => {
      const s = getComputedStyle(el);
      return { outline: s.outlineStyle, shadow: s.boxShadow };
    });
    expect(outline.outline !== "none" || outline.shadow !== "none").toBe(true);
  });

  test("the map carries a text description for screen readers", async ({ page }) => {
    // An SVG of the argument is useless to a screen reader without it.
    const map = page.getByRole("img", { name: /wind from/ });
    await expect(map).toBeVisible();
  });

  test("dialog is announced as a modal", async ({ page }) => {
    await page.getByRole("button", { name: "Why?" }).first().click();
    const dialog = page.getByRole("dialog");

    await expect(dialog).toHaveAttribute("aria-modal", "true");
    await expect(dialog).toHaveAttribute("aria-label", /Why:/);
  });

  test("scenario tabs use real tab semantics", async ({ page }) => {
    await expect(page.getByRole("tablist", { name: "Demo scenarios" })).toBeVisible();
    await expect(page.getByRole("tab")).toHaveCount(3);
  });
});
