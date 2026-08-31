import { describe, expect, it } from "vitest";
import { mapJobCatalogLine } from "./job-catalog-map";

describe("mapJobCatalogLine", () => {
  it("maps inner_hgb to booth English", () => {
    const mapped = mapJobCatalogLine("FIT", "start inner_hgb");
    expect(mapped.body).toBe("Train detector");
    expect(mapped.verb).toBe("FIT");
  });

  it("maps bootstrap resample ticks", () => {
    const mapped = mapJobCatalogLine("FIT", "bootstrap_ci family=mule resample 50/200");
    expect(mapped.body).toContain("mule");
    expect(mapped.body).toContain("50");
  });

  it("passes through quiet traffic progress lines", () => {
    const mapped = mapJobCatalogLine("COMMIT", "Quiet traffic — 800 of 2400 customers");
    expect(mapped.body).toBe("Quiet traffic — 800 of 2400 customers");
    expect(mapped.verb).toBe("COMMIT");
  });
});
