import { describe, expect, it } from "vitest";
import { liveAllowed } from "./useHonestyProbe";

describe("LIVE chip honesty", () => {
  it("is live only when search, LLM, and health are all true", () => {
    expect(
      liveAllowed(
        { identify_live_search: true, tavily_configured: true, llm: { configured: true } },
        { status: "ok" },
      ),
    ).toBe(true);
    expect(
      liveAllowed(
        { identify_live_search: false, tavily_configured: false, llm: { configured: true } },
        { status: "ok" },
      ),
    ).toBe(false);
    expect(
      liveAllowed(
        { identify_live_search: true, tavily_configured: true, llm: { configured: true } },
        { status: "down" },
      ),
    ).toBe(false);
  });
});
