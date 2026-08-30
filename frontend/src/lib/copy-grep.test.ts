import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const FORBIDDEN =
  /HITL|Loop M|inner_val|Scout|Curator|Seed Atlas|Researching|Coming soon|Planned|Decisioning|Arms Race|Simulation Console|AI-powered/;

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, name.name);
    if (name.isDirectory()) walk(p, acc);
    else if (/\.(tsx|ts)$/.test(name.name) && !name.name.endsWith(".test.ts")) acc.push(p);
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
      if (file.includes("HitlQueueTable")) continue;
      if (file.includes("TopicResearchPanel")) continue;
      if (file.includes("CopilotPage")) continue;
      if (file.includes("ArmsRace")) continue;
      if (file.includes("arms-race")) continue;
      if (file.includes("/decisioning/") && !file.includes("recall-fpr-data")) continue;
      if (file.includes("/simulation/")) continue;
      if (file.includes("GTestChart")) continue;
      if (file.includes("GuidedDemo")) continue;
      const text = readFileSync(file, "utf8");
      const strings = [...text.matchAll(/["'`]([^"'`]{0,200})["'`]/g)].map((m) => m[1]);
      for (const s of strings) {
        if (FORBIDDEN.test(s) && !s.includes("identify-hitl") && !s.includes("/identify/hitl") && !s.includes("loop-m") && !s.includes("loopm")) {
          leaks.push(`${file}: ${s}`);
        }
      }
    }
    expect(leaks).toEqual([]);
  });
});
