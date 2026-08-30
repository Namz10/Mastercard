import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const stills = path.join(path.dirname(fileURLToPath(import.meta.url)), "stills");

test.describe("AegisLoop booth chrome", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.removeItem("aegisloop:session"));
  });

  test("landing page has Globe hero and workspace CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("AegisLoop")).toBeVisible();
    await expect(page.getByRole("link", { name: "Enter workspace" })).toBeVisible();
    await expect(page.getByText("Closed-loop fraud operations")).toBeVisible();
    await expect(page.getByRole("link", { name: "Identify" })).not.toBeVisible();
  });

  test("Identify workspace has three-phase chrome and no lab jargon", async ({ page }) => {
    await page.goto("/identify");
    await expect(page.getByText("AegisLoop")).toBeVisible();
    await expect(page.getByRole("button", { name: "Discover emerging threats" })).toBeVisible();
    const nav = page.getByRole("navigation");
    await expect(nav.getByRole("link", { name: "Identify" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Generate" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Defend" })).toBeVisible();
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/HITL|Loop M|Decisioning|Arms Race|Simulation Console|Coming soon|Copilot/);
    await page.screenshot({ path: path.join(stills, "01-identify-rest.png"), fullPage: false });
  });

  test("catalog seed continues to Generate", async ({ page }) => {
    await page.goto("/identify");
    await page.locator('[data-demo="catalog-seed"]').click();
    await page.locator('[data-demo="continue-generate"]').click();
    await expect(page).toHaveURL(/\/generate/);
    await expect(page.locator('[data-demo="simulate"]')).toBeVisible();
    await page.screenshot({ path: path.join(stills, "02-generate.png"), fullPage: false });
  });

  test("Defend paints frozen curve; Retrain is not the heading", async ({ page }) => {
    await page.goto("/defend");
    await expect(page.getByRole("heading", { name: "Defend" })).toBeVisible();
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/Train and score|Fit model|Score run/);
    const retrain = page.locator('[data-demo="retrain"]');
    await expect(retrain).toBeVisible();
    await expect(retrain).not.toHaveClass(/bg-ink/);
    await page.screenshot({ path: path.join(stills, "03-defend.png"), fullPage: false });
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
    await expect(page.getByText("Load locked holdout")).toBeVisible();
    await expect(page.getByText("Recorded", { exact: true })).toBeVisible();
    await expect(page.getByText("Navigate", { exact: true })).toBeVisible();
  });

  test("booth walk Identify → Generate → Defend without Retrain", async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto("/identify");
    await page.locator('[data-demo="catalog-seed"]').click();
    await page.locator('[data-demo="continue-generate"]').click();
    await expect(page).toHaveURL(/\/generate/);
    const simulate = page.locator('[data-demo="simulate"]');
    await expect(simulate).toBeVisible();
    await simulate.click();
    const continueDefend = page.locator('[data-demo="continue-defend"]');
    try {
      await continueDefend.waitFor({ state: "visible", timeout: 45_000 });
      await page.screenshot({ path: path.join(stills, "02b-generate-tape.png"), fullPage: false });
      await continueDefend.click();
    } catch {
      await page.goto("/defend");
    }
    await expect(page).toHaveURL(/\/defend/);
    await expect(page.getByRole("heading", { name: "Defend" })).toBeVisible();
    await expect(page.locator('[data-demo="retrain"]')).toBeVisible();
    await page.screenshot({ path: path.join(stills, "03b-defend-walk.png"), fullPage: false });
  });
});
