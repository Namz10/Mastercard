import { describe, expect, it } from "vitest";
import { buildRecallFprCurve } from "@/features/decisioning/recall-fpr-data";
import type { ScoreMetrics } from "@/lib/api-types";

const metrics = (recall: number): ScoreMetrics => ({
  pass: true,
  n_eval: 10,
  ap_by_family: {},
  tpr_at_fpr: {},
  genuine_fp: 0.00032,
  f1_at_op: 0.9,
  precision_at_op: 0.9,
  recall_at_op: recall,
  binary_ap: 0.99,
  confusion_matrix: [],
  op_threshold: 0.001,
  recipe_hash: "x",
  model_freeze_id: "x",
  top_features: [],
});

describe("buildRecallFprCurve", () => {
  it("does not invent a 0.84 baseline when stage-1 is missing", () => {
    const pts = buildRecallFprCurve(metrics(0.985));
    expect(pts.every((p) => p.beforeRecall == null)).toBe(true);
    expect(pts.some((p) => Math.abs(p.recall - 0.985 * 0.84 * 100) < 0.2)).toBe(false);
  });

  it("adds a before series only when real before metrics exist", () => {
    const pts = buildRecallFprCurve(metrics(0.99), metrics(0.9));
    expect(pts.some((p) => p.beforeRecall != null)).toBe(true);
  });
});
