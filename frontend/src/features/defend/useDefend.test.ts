import { describe, expect, it } from "vitest";
import { scoreLooksBroken } from "@/features/defend/useDefend";
import type { ScoreMetrics } from "@/lib/api-types";

function metrics(overrides: Partial<ScoreMetrics> = {}): ScoreMetrics {
  return {
    pass: true,
    n_eval: 183025,
    ap_by_family: {},
    tpr_at_fpr: {
      "0.001": { tpr: 0.9867, fpr_target: 0.001 },
      "0.005": { tpr: 0.9947, fpr_target: 0.005 },
      "0.01": { tpr: 0.9957, fpr_target: 0.01 },
    },
    genuine_fp: 0.000318,
    f1_at_op: 0,
    precision_at_op: 0.9857,
    recall_at_op: 0.9852,
    binary_ap: 0.9985,
    confusion_matrix: [],
    op_threshold: 0.915,
    recipe_hash: "frozen",
    model_freeze_id: "frozen",
    top_features: [],
    ...overrides,
  };
}

describe("scoreLooksBroken", () => {
  it("accepts champion freeze metrics", () => {
    expect(scoreLooksBroken(metrics())).toBe(false);
  });

  it("rejects photography-day legacy pack (~8% FPR, flat 100% recall)", () => {
    expect(
      scoreLooksBroken(
        metrics({
          genuine_fp: 0.08,
          recall_at_op: 0.9997,
          tpr_at_fpr: { "0.001": 0.9997, "0.005": 0.9997, "0.01": 0.9997 },
        }),
      ),
    ).toBe(true);
  });

  it("rejects flat tpr_at_fpr curves", () => {
    expect(
      scoreLooksBroken(
        metrics({
          tpr_at_fpr: { "0.001": 0.99, "0.005": 0.99, "0.01": 0.99 },
        }),
      ),
    ).toBe(true);
  });
});
