import { describe, expect, it } from "vitest";
import { dedupeHitlItems, pendingHitlItems } from "./hitl-dedupe";
import type { HitlItem } from "./api-types";

function item(partial: Partial<HitlItem> & Pick<HitlItem, "vector_id">): HitlItem {
  return {
    technique_id: "T01",
    nearest_technique_id: "T01",
    tier_badges: [],
    source_urls: null,
    vector_class: null,
    generate_mode: null,
    simulatable_signals_preview: null,
    confidence_level: null,
    corroboration_type: null,
    name: "Mule funnel",
    field_diff: null,
    ...partial,
  };
}

describe("dedupeHitlItems", () => {
  it("drops duplicate vector_id and technique+name pairs", () => {
    const rows = [
      item({ vector_id: "a", technique_id: "T09", name: "Deepfake" }),
      item({ vector_id: "b", technique_id: "T09", name: "Deepfake" }),
      item({ vector_id: "c", technique_id: "T01", name: "Mule" }),
    ];
    expect(dedupeHitlItems(rows).map((r) => r.vector_id)).toEqual(["a", "c"]);
  });

  it("pendingHitlItems ignores in_catalog rows", () => {
    const rows = [
      item({ vector_id: "a", disposition: "review" }),
      item({ vector_id: "b", disposition: "in_catalog", name: "Catalog only" }),
    ];
    expect(pendingHitlItems(rows).map((r) => r.vector_id)).toEqual(["a"]);
  });
});
