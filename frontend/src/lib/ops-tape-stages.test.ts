import { describe, expect, it } from "vitest";
import { DEFEND_FIT_STAGES, stagesToLines } from "./ops-tape-stages";

describe("stagesToLines", () => {
  it("marks first stage active at t=0", () => {
    const lines = stagesToLines(DEFEND_FIT_STAGES, 0, false);
    expect(lines[0].status).toBe("active");
    expect(lines[1].status).toBe("pending");
  });

  it("advances bootstrap body with resample count", () => {
    const lines = stagesToLines(DEFEND_FIT_STAGES, 6000, false);
    const bootstrap = lines.find((l) => l.id === "bootstrap");
    expect(bootstrap?.body).toMatch(/of 200/);
    expect(bootstrap?.status).toBe("active");
  });

  it("marks all done when job completes", () => {
    const lines = stagesToLines(DEFEND_FIT_STAGES, 25000, true);
    expect(lines.every((l) => l.status === "done")).toBe(true);
  });
});
