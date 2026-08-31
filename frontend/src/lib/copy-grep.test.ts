import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const FORBIDDEN =
  /HITL|Loop M|inner_val|Scout|Curator|Seed Atlas|Researching|Coming soon|Planned|Decisioning|Arms Race|Simulation Console|AI-powered/;
const ALLOWED =
  /Optuna|hyperparameter tuning|feedback loop|Improve defense/i;
const VISUAL = /rounded-2xl|#2563EB|#6366F1/;

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, name.name);
    if (name.isDirectory()) {
      if (name.name === "arms-race" || name.name === "simulation" || name.name === "copilot" || name.name === "demo") {
        continue;
      }
      walk(p, acc);
    } else if (/\.(tsx|ts)$/.test(name.name) && !name.name.endsWith(".test.ts")) acc.push(p);
  }
  return acc;
}

describe("forbidden glass copy", () => {
  it("does not leak lab jargon in user-visible strings", () => {
    const root = join(process.cwd(), "src");
    const files = walk(root);
    const leaks: string[] = [];
    for (const file of files) {
      if (file.includes("api-types.ts")) continue;
      if (file.includes("useIdentify.ts")) continue;
      if (file.includes("/decisioning/") && !file.includes("recall-fpr-data")) continue;
      if (file.includes("GTestChart")) continue;
      const text = readFileSync(file, "utf8");
      const strings = [...text.matchAll(/["'`]([^"'`]{0,200})["'`]/g)].map((m) => m[1]);
      for (const s of strings) {
        if (FORBIDDEN.test(s) && !ALLOWED.test(s) && !s.includes("identify-hitl") && !s.includes("/identify/hitl") && !s.includes("loop-m") && !s.includes("loopm")) {
          leaks.push(`${file}: ${s}`);
        }
      }
      if (VISUAL.test(text) && !file.includes("Copilot")) {
        leaks.push(`${file}: visual token`);
      }
    }
    expect(leaks).toEqual([]);
  });
});
