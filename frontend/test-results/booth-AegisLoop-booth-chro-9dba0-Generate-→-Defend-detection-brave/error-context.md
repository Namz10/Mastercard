# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: booth.spec.ts >> AegisLoop booth chrome >> booth walk Identify → Generate → Defend detection
- Location: e2e/booth.spec.ts:70:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('[data-demo="ops-tape"], [data-demo="metric-hero"], [data-demo="detection-fidelity-block"], [data-demo="detection-await-fidelity"]').first()
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for locator('[data-demo="ops-tape"], [data-demo="metric-hero"], [data-demo="detection-fidelity-block"], [data-demo="detection-await-fidelity"]').first()

```

```yaml
- complementary:
  - button "LIVE search + LLM"
  - button "Collapse sidebar"
  - text: A AegisLoop Closed-loop booth
  - navigation "Phases":
    - button "Search"
    - text: Closed loop
    - link "Identify":
      - /url: /identify
    - link "Generate":
      - /url: /generate
    - link "Defend":
      - /url: /defend
- navigation "Stage navigation":
  - link "Detection":
    - /url: /defend/detection
  - text: ·
  - link "Interventions":
    - /url: /defend/interventions
  - text: ·
  - link "Improve defense":
    - /url: /defend/feedback
  - text: ·
  - link "Optuna":
    - /url: /defend/hyperparameters
- button "⌘K"
- main:
  - heading "Detection" [level=1]
  - paragraph: Holdout recall at a genuine false-alarm cap.
  - text: SCORE awaiting operator
  - heading "Score on a simulated corpus first" [level=2]
  - paragraph: No score on glass. Continue from Generate, or load a recorded pack (⌘K).
  - button "Go to Generate"
  - link "Simulate payment traffic":
    - /url: /generate
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import path from "node:path";
  3  | import { fileURLToPath } from "node:url";
  4  | 
  5  | const stills = path.join(path.dirname(fileURLToPath(import.meta.url)), "stills");
  6  | 
  7  | test.describe("AegisLoop booth chrome", () => {
  8  |   test.beforeEach(async ({ page }) => {
  9  |     await page.addInitScript(() => {
  10 |       localStorage.removeItem("aegisloop:session");
  11 |       sessionStorage.removeItem("aegisloop:session");
  12 |     });
  13 |   });
  14 | 
  15 |   test("landing page has Globe hero and workspace CTA", async ({ page }) => {
  16 |     await page.goto("/");
  17 |     await expect(page.getByText("AegisLoop")).toBeVisible();
  18 |     await expect(page.getByRole("link", { name: "Enter workspace" })).toBeVisible();
  19 |     await expect(page.getByText("Closed-loop fraud operations")).toBeVisible();
  20 |     await expect(page.getByRole("link", { name: "Identify" })).not.toBeVisible();
  21 |   });
  22 | 
  23 |   test("Identify landscape has discover CTA and stage pills", async ({ page }) => {
  24 |     await page.goto("/identify");
  25 |     await expect(page.getByText("AegisLoop")).toBeVisible();
  26 |     await expect(page.getByRole("button", { name: "Discover emerging threats" })).toBeVisible();
  27 |     await expect(page.locator('[data-demo="stage-pill-landscape"]')).toBeVisible();
  28 |     const body = await page.locator("body").innerText();
  29 |     expect(body).not.toMatch(/HITL|Loop M|Decisioning|Arms Race|Simulation Console|Coming soon|Copilot/);
  30 |     await expect(page.locator('[data-demo="stage-pill-discover"]')).toBeVisible();
  31 |     await page.screenshot({ path: path.join(stills, "01-identify-landscape.png"), fullPage: false });
  32 |   });
  33 | 
  34 |   test("catalog seed continues to Generate", async ({ page }) => {
  35 |     await page.goto("/identify");
  36 |     await page.locator('[data-demo="catalog-seed"]').click();
  37 |     await page.locator('[data-demo="continue-generate"]').click();
  38 |     await expect(page).toHaveURL(/\/generate/);
  39 |     await expect(page.getByRole("button", { name: "Simulate payment traffic" })).toBeVisible();
  40 |     await page.screenshot({ path: path.join(stills, "02-generate.png"), fullPage: false });
  41 |   });
  42 | 
  43 |   test("Defend detection page shows guided empty or scoring tape", async ({ page }) => {
  44 |     await page.goto("/defend/detection");
  45 |     await expect(page.getByRole("heading", { name: "Detection" })).toBeVisible();
  46 |     const body = await page.locator("body").innerText();
  47 |     expect(body).not.toMatch(/Train and score|Fit model|Score run|HITL|Loop M/);
  48 |     await expect(
  49 |       page.getByText(/No score on glass|Continue to Generate|Scoring this run/i).first(),
  50 |     ).toBeVisible();
  51 |     await page.screenshot({ path: path.join(stills, "03-defend-detection.png"), fullPage: false });
  52 |   });
  53 | 
  54 |   test("command palette opens with Ctrl+K", async ({ page }) => {
  55 |     await page.goto("/identify");
  56 |     await page.evaluate(() => {
  57 |       window.dispatchEvent(
  58 |         new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true, cancelable: true }),
  59 |       );
  60 |     });
  61 |     const input = page.getByPlaceholder("Command");
  62 |     if (!(await input.isVisible().catch(() => false))) {
  63 |       await page.locator('[data-demo="command-palette"]').click();
  64 |     }
  65 |     await expect(page.getByPlaceholder("Command")).toBeVisible();
  66 |     await expect(page.getByText("Run booth demo")).toBeVisible();
  67 |     await expect(page.getByText("Load locked holdout")).toBeVisible();
  68 |   });
  69 | 
  70 |   test("booth walk Identify → Generate → Defend detection", async ({ page }) => {
  71 |     test.setTimeout(90_000);
  72 |     await page.goto("/identify");
  73 |     await page.locator('[data-demo="catalog-seed"]').click();
  74 |     await page.locator('[data-demo="continue-generate"]').click();
  75 |     await expect(page).toHaveURL(/\/generate/);
  76 |     const simulate = page.getByRole("button", { name: "Simulate payment traffic" });
  77 |     await expect(simulate).toBeVisible();
  78 |     await simulate.click();
  79 |     const continueDefend = page.locator('[data-demo="continue-defend"]');
  80 |     try {
  81 |       await continueDefend.waitFor({ state: "visible", timeout: 45_000 });
  82 |       await page.screenshot({ path: path.join(stills, "02b-generate-tape.png"), fullPage: false });
  83 |       await continueDefend.click();
  84 |     } catch {
  85 |       await page.goto("/defend/detection");
  86 |     }
  87 |     await expect(page).toHaveURL(/\/defend\/detection/);
  88 |     await expect(page.getByRole("heading", { name: "Detection" })).toBeVisible();
  89 |     await expect(
  90 |       page
  91 |         .locator(
  92 |           '[data-demo="ops-tape"], [data-demo="metric-hero"], [data-demo="detection-fidelity-block"], [data-demo="detection-await-fidelity"]',
  93 |         )
  94 |         .first(),
> 95 |     ).toBeVisible({ timeout: 15_000 });
     |       ^ Error: expect(locator).toBeVisible() failed
  96 |     await page.screenshot({ path: path.join(stills, "03b-defend-walk.png"), fullPage: false });
  97 |   });
  98 | });
  99 | 
```