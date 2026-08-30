import { describe, expect, it } from "vitest";
import { RECORDED_MIN_MS, scheduleOffsets } from "./pace-events";

describe("recorded Identify pacing", () => {
  it("stretches a fast dump to at least 12s", () => {
    const offsets = scheduleOffsets([
      { t: 0 },
      { t: 50 },
      { t: 120 },
      { t: 200 },
    ]);
    expect(offsets[0]).toBe(0);
    expect(offsets[offsets.length - 1]).toBeGreaterThanOrEqual(RECORDED_MIN_MS);
  });

  it("keeps a 15s fixture inside 12–18s", () => {
    const offsets = scheduleOffsets([
      { t: 0 },
      { t: 800 },
      { t: 6000 },
      { t: 15000 },
    ]);
    expect(offsets[offsets.length - 1]).toBe(15_000);
  });

  it("spreads events without t over 12s", () => {
    const offsets = scheduleOffsets([{}, {}, {}, {}]);
    expect(offsets[0]).toBe(0);
    expect(offsets[offsets.length - 1]).toBe(RECORDED_MIN_MS);
  });
});
