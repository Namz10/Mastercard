import type { OpsTapeStage } from "./ops-tape-types";

/** Detection fit→score pipeline — elapsed bands approximate real [fit] timing */
export const DEFEND_FIT_STAGES: OpsTapeStage[] = [
  { id: "load", verb: "FIT", body: "Load holdout parquet", afterMs: 0 },
  { id: "encode", verb: "FIT", body: "Encode features", afterMs: 400 },
  { id: "inner_hgb", verb: "FIT", body: "Train detector (HGBM)", afterMs: 900 },
  { id: "isolation", verb: "FIT", body: "Isolation forest", afterMs: 2200 },
  { id: "outer_hgb", verb: "FIT", body: "Outer model", afterMs: 2800 },
  { id: "perm", verb: "FIT", body: "Which features moved the score", afterMs: 3800 },
  {
    id: "bootstrap",
    verb: "FIT",
    body: "Checking stability on holdout",
    afterMs: 4500,
    activeBody: (ms) => {
      const n = Math.min(200, Math.floor((ms - 4500) / 80) + 1);
      return `Checking stability — ${n} of 200 holdout resamples`;
    },
  },
  { id: "brake", verb: "APPLY", body: "Policy histogram at the operating point", afterMs: 18000 },
  { id: "score", verb: "SCORE", body: "Score operating point on locked holdout", afterMs: 19500 },
];

export const GENERATE_STAGES: OpsTapeStage[] = [
  { id: "commit", verb: "COMMIT", body: "Simulate payment traffic", afterMs: 0 },
  { id: "inject", verb: "INJECT", body: "Inject fraud families from approved recipes", afterMs: 8000 },
  { id: "mule", verb: "INJECT", body: "Layer mule fan-in and cash-out paths", afterMs: 22000 },
  { id: "fidelity", verb: "FIDELITY", body: "PSI · fraud-rate band · mule fan-in", afterMs: 45000 },
];

export function feedbackStages(missFamily: string): OpsTapeStage[] {
  const label = missFamily.replace(/_/g, " ");
  return [
    { id: "miss", verb: "RETRAIN", body: `Take the miss family — ${label}`, afterMs: 0 },
    { id: "extra", verb: "RETRAIN", body: `Add extra training of ${label} type`, afterMs: 800 },
    { id: "refit", verb: "FIT", body: "Refit detector on expanded training", afterMs: 2000 },
    { id: "holdout", verb: "SCORE", body: "Grade on a new holdout — cannot mark own homework", afterMs: 12000 },
    { id: "compare", verb: "SCORE", body: "Compare before vs after", afterMs: 20000 },
  ];
}

export const OPTUNA_STAGES: OpsTapeStage[] = [
  { id: "search", verb: "FIT", body: "Search settings on validation · holdout frozen", afterMs: 0 },
  { id: "trials", verb: "FIT", body: "Trials on validation fold only", afterMs: 1500 },
  { id: "refit", verb: "FIT", body: "Refit with best settings", afterMs: 6000 },
  { id: "compare", verb: "SCORE", body: "Compare base · feedback · Optuna", afterMs: 12000 },
];

export function stagesToLines(
  stages: OpsTapeStage[],
  elapsedMs: number,
  done: boolean,
): import("./ops-tape-types").OpsTapeLine[] {
  let activeIdx = 0;
  for (let i = stages.length - 1; i >= 0; i--) {
    if (elapsedMs >= stages[i].afterMs) {
      activeIdx = i;
      break;
    }
  }
  return stages.map((stage, i) => {
    let lineStatus: "pending" | "active" | "done";
    if (done) lineStatus = "done";
    else if (i < activeIdx) lineStatus = "done";
    else if (i === activeIdx) lineStatus = "active";
    else lineStatus = "pending";

    const body =
      lineStatus === "active" && stage.activeBody ? stage.activeBody(elapsedMs) : stage.body;

    return {
      id: stage.id,
      verb: stage.verb,
      body,
      status: lineStatus,
    };
  });
}
