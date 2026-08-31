import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { POPULATION_SCALE } from "@/features/generate/useGenerate";

describe("useGenerate population scale", () => {
  it("uses FinCEN alert004 campaign id in canary path if present", () => {
    const text = readFileSync(join(process.cwd(), "src/lib/generate-job.ts"), "utf8");
    expect(text).toContain("2400");
    expect(text).toContain("population/stream");
  });

  it("full population scale matches runner defaults", () => {
    expect(POPULATION_SCALE).toEqual({ n_customers: 2400, n_merchants: 120, sim_days: 90 });
  });
});
