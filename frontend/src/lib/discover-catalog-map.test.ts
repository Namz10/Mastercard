import { describe, expect, it } from "vitest";
import { mapDiscoverCatalogLine } from "./discover-catalog-map";

describe("mapDiscoverCatalogLine", () => {
  it("strips Tavily vendor name from progress bodies", () => {
    const mapped = mapDiscoverCatalogLine("COLLECT", "Tavily search · FTC press payment fraud");
    expect(mapped.body).toContain("Search —");
    expect(mapped.body.toLowerCase()).not.toContain("tavily");
  });

  it("maps candidate progress to rank step", () => {
    const mapped = mapDiscoverCatalogLine("COLLECT", "Tavily · 60 candidates so far");
    expect(mapped.verb).toBe("RANK");
    expect(mapped.body).toContain("Rank");
  });

  it("shows started collect line without skipping", () => {
    const mapped = mapDiscoverCatalogLine("COLLECT", "Collect started");
    expect(mapped.skip).toBeUndefined();
    expect(mapped.body).toContain("collectors");
  });
});
