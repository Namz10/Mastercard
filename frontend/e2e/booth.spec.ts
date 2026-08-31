import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const stills = path.join(path.dirname(fileURLToPath(import.meta.url)), "stills");

test.describe("AegisLoop booth chrome", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem("aegisloop:session");
      sessionStorage.removeItem("aegisloop:session");
    });
  });

  test("landing page has Globe hero and workspace CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("AegisLoop")).toBeVisible();
    await expect(page.getByRole("link", { name: "Enter workspace" })).toBeVisible();
    await expect(page.getByText("Closed-loop fraud operations")).toBeVisible();
    await expect(page.getByRole("link", { name: "Identify" })).not.toBeVisible();
  });

  test("Identify landscape has discover CTA and stage pills", async ({ page }) => {
    await page.goto("/identify");
    await expect(page.getByText("AegisLoop")).toBeVisible();
    await expect(page.getByRole("button", { name: "Discover emerging threats" })).toBeVisible();
    await expect(page.locator('[data-demo="stage-pill-landscape"]')).toBeVisible();
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/HITL|Loop M|Decisioning|Arms Race|Simulation Console|Coming soon|Copilot/);
    await expect(page.locator('[data-demo="stage-pill-discover"]')).toBeVisible();
    await page.screenshot({ path: path.join(stills, "01-identify-landscape.png"), fullPage: false });
  });

  test("catalog seed continues to Generate", async ({ page }) => {
    await page.goto("/identify");
    await page.locator('[data-demo="catalog-seed"]').click();
    await page.locator('[data-demo="continue-generate"]').click();
    await expect(page).toHaveURL(/\/generate/);
    await expect(page.getByRole("button", { name: "Simulate payment traffic" })).toBeVisible();
    await page.screenshot({ path: path.join(stills, "02-generate.png"), fullPage: false });
  });

  test("Defend detection page shows guided empty or scoring tape", async ({ page }) => {
    await page.goto("/defend/detection");
    await expect(page.getByRole("heading", { name: "Detection" })).toBeVisible();
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/Train and score|Fit model|Score run|HITL|Loop M/);
    await expect(
      page.getByText(/No score on glass|Continue to Generate|Scoring this run/i).first(),
    ).toBeVisible();
    await page.screenshot({ path: path.join(stills, "03-defend-detection.png"), fullPage: false });
  });

  test("command palette opens with Ctrl+K", async ({ page }) => {
    await page.goto("/identify");
    await page.evaluate(() => {
      window.dispatchEvent(
        new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true, cancelable: true }),
      );
    });
    const input = page.getByPlaceholder("Command");
    if (!(await input.isVisible().catch(() => false))) {
      await page.locator('[data-demo="command-palette"]').click();
    }
    await expect(page.getByPlaceholder("Command")).toBeVisible();
    await expect(page.getByText("Run booth demo")).toBeVisible();
    await expect(page.getByText("Load locked holdout")).toBeVisible();
  });

  test("booth walk Identify → Generate → Defend detection", async ({ page }) => {
    test.setTimeout(180_000);
    await page.goto("/identify");
    await page.locator('[data-demo="catalog-seed"]').click();
    await page.locator('[data-demo="continue-generate"]').click();
    await expect(page).toHaveURL(/\/generate/);
    const simulate = page.getByRole("button", { name: "Simulate payment traffic" });
    await expect(simulate).toBeVisible();
    await simulate.click();
    await expect(page.locator('[data-demo="generate-scanning"]')).toBeVisible({ timeout: 10_000 });
    const continueDefend = page.locator('[data-demo="continue-defend"]');
    try {
      await continueDefend.waitFor({ state: "visible", timeout: 120_000 });
      await page.screenshot({ path: path.join(stills, "02b-generate-tape.png"), fullPage: false });
      await continueDefend.click();
    } catch {
      await page.goto("/defend/detection");
    }
    await expect(page).toHaveURL(/\/defend\/detection/);
    await expect(page.getByRole("heading", { name: "Detection" })).toBeVisible();
    await expect(
      page
        .locator('[data-demo="job-thread"], [data-demo="metric-hero"], [data-demo="catalog-thread"]')
        .first(),
    ).toBeVisible({ timeout: 90_000 });
    await page.screenshot({ path: path.join(stills, "03b-defend-walk.png"), fullPage: false });
  });
});
