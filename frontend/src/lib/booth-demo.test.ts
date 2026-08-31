import { describe, expect, it } from "vitest";
import { BOOTH_DEMO_LABEL } from "./booth-demo";
import { COPY } from "./copy";

describe("booth-demo", () => {
  it("exposes a stable label for the palette", () => {
    expect(BOOTH_DEMO_LABEL).toBe(COPY.palette.boothDemo);
  });

  it("runs Path B in order", async () => {
    const steps: string[] = [];
    await import("./booth-demo").then(({ runBoothDemo }) =>
      runBoothDemo({
        navigate: (path) => steps.push(`nav:${path}`),
        simulate: async () => {
          steps.push("simulate");
        },
        loadScore: async () => {
          steps.push("loadScore");
        },
      }),
    );
    expect(steps).toEqual(["nav:/generate", "simulate", "loadScore", "nav:/defend/detection"]);
  });
});
