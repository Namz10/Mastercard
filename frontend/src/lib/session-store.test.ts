import { afterEach, describe, expect, it } from "vitest";
import {
  acceptCatalogSeed,
  approveAttack,
  beginBoothSession,
  canScoreGenerate,
  clearDefendIfStale,
  getSession,
  isDefendScoreCurrent,
  resetSessionForTests,
  setDefendScore,
  setGenerateRun,
  setRetrainResult,
} from "./session-store";
import type { ScoreResponse } from "./api-types";

const score = (id: string): ScoreResponse => ({
  run_id: "g1",
  model_run_id: id,
  metrics: {
    pass: true,
    n_eval: 100,
    ap_by_family: { app_fraud: { ap: 0.4 } },
    tpr_at_fpr: { "0.001": 0.98 },
    genuine_fp: 0.00032,
    f1_at_op: 0.9,
    precision_at_op: 0.9,
    recall_at_op: 0.985,
    binary_ap: 0.99,
    confusion_matrix: [[1, 0], [0, 1]],
    op_threshold: 0.001,
    recipe_hash: "x",
    model_freeze_id: "x",
    top_features: [],
  },
  action_histogram: { allow: 10 },
  split: "gtest",
  recipe_hash: "x",
  model_freeze_id: "x",
});

describe("aegisloop:session", () => {
  afterEach(() => resetSessionForTests());

  it("clears defend when a new generate run is written", () => {
    setDefendScore(score("m1"), "m1");
    expect(getSession().defend.score).not.toBeNull();
    setGenerateRun("run-2", 42, "full", true, 100);
    const s = getSession();
    expect(s.generate.runId).toBe("run-2");
    expect(s.defend.score).toBeNull();
    expect(s.defend.loopResult).toBeNull();
    expect(s.defend.modelRunId).toBeNull();
  });

  it("stores modelRunId from retrain, not generate run_id", () => {
    setGenerateRun("gen-1", 42, "full", true, 50);
    setDefendScore(score("gen-1"), "gen-1");
    setRetrainResult(score("gen-1__loopm-train"), "gen-1__loopm-train", "T13", { ok: true });
    expect(getSession().defend.modelRunId).toBe("gen-1__loopm-train");
    expect(getSession().ui.highlightTechniqueId).toBe("T13");
  });

  it("does not clear generate when accepting catalog seed", () => {
    setGenerateRun("gen-1", 42, "full", true, 50);
    acceptCatalogSeed();
    expect(getSession().generate.runId).toBe("gen-1");
    expect(getSession().identify.approved[0]?.id).toBe("catalog-seed");
  });

  it("dedupes approve by techniqueId", () => {
    approveAttack({ id: "v1", techniqueId: "T13", name: "A" });
    approveAttack({ id: "v2", techniqueId: "T13", name: "B" });
    expect(getSession().identify.approved).toHaveLength(1);
  });

  it("defaults to live source chip", () => {
    resetSessionForTests();
    expect(getSession().ui.sourceChip).toBe("live");
    expect(getSession().identify.source).toBe("live");
  });

  it("beginBoothSession clears prior progress", () => {
    setGenerateRun("run-1", 42, "full", true, 100);
    setDefendScore(score("m1"), "m1");
    beginBoothSession();
    const s = getSession();
    expect(s.generate.runId).toBeNull();
    expect(s.defend.score).toBeNull();
    expect(s.identify.approved).toHaveLength(0);
  });

  it("clearDefendIfStale drops score when run_id mismatches", () => {
    setGenerateRun("run-a", 42, "full", true, 100);
    setDefendScore({ ...score("m1"), run_id: "run-b" }, "m1");
    clearDefendIfStale();
    expect(getSession().defend.score).toBeNull();
    expect(isDefendScoreCurrent(getSession())).toBe(false);
  });

  it("canScoreGenerate when run exists regardless of fidelity", () => {
    setGenerateRun("run-a", 42, "full", false, 5474, { normal: 5000, mule: 100 }, 5.0, [
      "psi_amount=0.9>0.25",
    ]);
    expect(canScoreGenerate(getSession())).toBe(true);
  });
});
