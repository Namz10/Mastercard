import { describe, expect, it } from "vitest";
import { buildLedgerTape } from "./ledger-tape";

describe("ledger tape", () => {
  it("caps at 40 rows and is seeded", () => {
    const counts = { normal: 8000, mule: 400, app_fraud: 200, ato: 80 };
    const a = buildLedgerTape(counts, 42, 40);
    const b = buildLedgerTape(counts, 42, 40);
    expect(a).toHaveLength(40);
    expect(a).toEqual(b);
    expect(a[0].parties).toMatch(/→/);
    expect(a[0].clock).toMatch(/\d{2}:\d{2}:\d{2}/);
    expect(a.some((r) => r.family !== "normal")).toBe(true);
    expect(a.some((r) => r.family === "mule")).toBe(true);
  });
});
