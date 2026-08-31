import { afterEach, describe, expect, it } from "vitest";
import { getSession, resetSessionForTests } from "./session-store";
import {
  defendStageUnlocked,
  identifyStageUnlocked,
} from "./stage-unlock";

describe("stage-unlock", () => {
  afterEach(() => resetSessionForTests());

  it("always unlocks landscape and discover", () => {
    const s = getSession();
    expect(identifyStageUnlocked("landscape", s)).toBe(true);
    expect(identifyStageUnlocked("discover", s)).toBe(true);
  });

  it("unlocks defend detection when generate run exists", () => {
    const s = getSession();
    s.generate.runId = "r1";
    s.generate.fidelityPass = false;
    expect(defendStageUnlocked("detection", s)).toBe(true);
    s.generate.fidelityPass = true;
    expect(defendStageUnlocked("detection", s)).toBe(true);
  });

  it("blocks defend detection without a generate run", () => {
    const s = getSession();
    expect(defendStageUnlocked("detection", s)).toBe(false);
  });

  it("unlocks hyperparameters after loop or score", () => {
    const s = getSession();
    s.generate.runId = "r1";
    s.generate.fidelityPass = true;
    s.defend.score = {
      run_id: "r1",
      model_run_id: "m1",
      metrics: {
        pass: true,
        n_eval: 1,
        ap_by_family: {},
        tpr_at_fpr: {},
        genuine_fp: 0.001,
        f1_at_op: 0,
        precision_at_op: 0,
        recall_at_op: 0.9,
        binary_ap: 0.9,
        confusion_matrix: [],
        op_threshold: 0.5,
        recipe_hash: "x",
        model_freeze_id: "x",
        top_features: [],
      },
      action_histogram: {},
      split: "gtest",
      recipe_hash: "x",
      model_freeze_id: "x",
    };
    expect(defendStageUnlocked("hyperparameters", s)).toBe(true);
  });
});
