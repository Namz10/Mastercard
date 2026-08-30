import { describe, expect, it } from "vitest";
import { buildRecallFprCurve, recallYDomain } from "@/features/decisioning/recall-fpr-data";
import type { ScoreMetrics } from "@/lib/api-types";

const CHAMPION_TPR = {
  "0.001": { tpr: 0.9867, fpr_target: 0.001 },
  "0.005": { tpr: 0.9947425181989754, fpr_target: 0.005 },
  "0.01": { tpr: 0.9956861687786466, fpr_target: 0.01 },
  "0.000318349": { tpr: 0.9851609657947686, fpr_target: 0.00031834860848147715 },
};

function metrics(overrides: Partial<ScoreMetrics> = {}): ScoreMetrics {
  return {
    pass: true,
    n_eval: 183025,
    ap_by_family: {},
    tpr_at_fpr: CHAMPION_TPR,
    genuine_fp: 0.00031834860848147715,
    f1_at_op: 0,
    precision_at_op: 0.9857,
    recall_at_op: 0.9851609657947686,
    binary_ap: 0.9985,
    confusion_matrix: [],
    op_threshold: 0.915,
    recipe_hash: "frozen",
    model_freeze_id: "frozen",
    top_features: [],
    ...overrides,
  };
}

describe("buildRecallFprCurve", () => {
  it("does not invent a 0.84 baseline when stage-1 is missing", () => {
    const pts = buildRecallFprCurve(metrics({ tpr_at_fpr: {}, recall_at_op: 0.985 }));
    expect(pts.every((p) => p.beforeRecall == null)).toBe(true);
    expect(pts.some((p) => Math.abs(p.recall - 0.985 * 0.84 * 100) < 0.2)).toBe(false);
  });

  it("adds a before series only when real before metrics exist", () => {
    const pts = buildRecallFprCurve(metrics(), metrics({ recall_at_op: 0.9, tpr_at_fpr: { "0.001": 0.9 } }));
    expect(pts.some((p) => p.beforeRecall != null)).toBe(true);
  });

  it("produces distinct recall at each FPR anchor from champion freeze curve", () => {
    const pts = buildRecallFprCurve(metrics());
    expect(pts).toHaveLength(4);
    const recalls = pts.map((p) => p.recall);
    expect(Math.max(...recalls) - Math.min(...recalls)).toBeGreaterThan(0.5);
    expect(pts[0].recall).toBeLessThan(pts[1].recall);
    expect(pts[1].recall).toBeLessThan(pts[2].recall);
    expect(Math.abs(pts[1].recall - 98.67)).toBeLessThan(0.05);
    expect(Math.abs(pts[0].recall - 98.56)).toBeLessThan(0.15);
  });
});

describe("recallYDomain", () => {
  it("zooms Y axis so the curve is not flat", () => {
    const pts = buildRecallFprCurve(metrics());
    const [lo, hi] = recallYDomain(pts);
    expect(lo).toBeGreaterThan(90);
    expect(hi - lo).toBeLessThan(5);
  });
});
