import type { LoopMResponse, ScoreMetrics } from "@/lib/api-types";

export interface BarMetricRow {
  metric: string;
  baseModel: number;
  postFeedback: number;
}

export interface CoEvolutionPoint {
  gen: string;
  evasion: number | null;
  prAuc: number | null;
  genuineFpr: number | null;
  projected?: boolean;
}

export interface ArmsRaceViewModel {
  family: string;
  gtestSeed: number;
  trainSeed: number;
  nExtra: number;
  capPct: number;
  catalogSolved: boolean;
  apDelta: number;
  apVerdict: string;
  pass: boolean;
  genuineFpBefore: number;
  genuineFpAfter: number;
  genuineFpOk: boolean;
  barChart: {
    rows: BarMetricRow[];
    family: string;
    apDelta: number;
    verdict: string;
  };
  coEvolution: {
    points: CoEvolutionPoint[];
    family: string;
    gtestSeed: number;
    trainSeed: number;
    apDelta: number;
    pass: boolean;
  };
  ledger: {
    family: string;
    nExtra: number;
    capPct: number;
    g0: LedgerMetrics;
    g1: LedgerMetrics;
  };
}

export interface LedgerMetrics {
  binaryAp: number;
  precision: number;
  recall: number;
  genuineFpr: number;
  prAuc?: number;
  apDelta?: number;
  evasion: number;
}

function pct(n: number, digits = 0): string {
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatLedgerPct(n: number, digits = 0): string {
  return pct(n, digits);
}

function familyAp(metrics: ScoreMetrics | undefined, family: string): number | null {
  const entry = metrics?.ap_by_family?.[family];
  return entry?.ap ?? null;
}

function evasionFromRecall(recall: number): number {
  return Math.max(0, Math.min(1, 1 - recall));
}

function num(value: number | null | undefined, fallback = 0): number {
  return value != null && !Number.isNaN(value) ? value : fallback;
}

/** Build view model solely from a completed Loop M API response. */
export function buildArmsRaceViewModel(loopM: LoopMResponse | null): ArmsRaceViewModel | null {
  if (!loopM?.metrics?.gtest_before || !loopM?.metrics?.gtest_after) return null;

  const before = loopM.metrics.gtest_before;
  const after = loopM.metrics.gtest_after;
  const family = loopM.comparison?.family ?? loopM.miss_family;
  if (!family) return null;

  const baseBinaryAp = num(before.binary_ap);
  const postBinaryAp = num(after.binary_ap);
  const basePrecision = num(before.precision_at_op);
  const postPrecision = num(after.precision_at_op);
  const baseRecall = num(before.recall_at_op);
  const postRecall = num(after.recall_at_op);

  const apDelta = num(loopM.comparison?.ap_delta, postBinaryAp - baseBinaryAp);
  const g0PrAuc = num(loopM.comparison?.ap_before ?? familyAp(before, family), baseBinaryAp);
  const g1PrAuc = num(loopM.comparison?.ap_after ?? familyAp(after, family), postBinaryAp);

  const g0Evasion = evasionFromRecall(baseRecall);
  const recallGain = postRecall - baseRecall;
  const g1Evasion =
    recallGain > 0 ? Math.max(0, g0Evasion - recallGain) : Math.max(0, g0Evasion * (1 - Math.max(0, apDelta)));

  const genuineFpBefore = num(loopM.comparison?.genuine_fp_before, before.genuine_fp);
  const genuineFpAfter = num(loopM.comparison?.genuine_fp_after, after.genuine_fp);

  const capFrac = loopM.extra_row_cap_frac ?? 0.15;
  const capPct = Math.round(capFrac * 100);
  const nExtra = loopM.n_extra ?? 0;

  const apVerdict = loopM.comparison?.ap_verdict ?? "unknown";
  const pass = loopM.metrics.pass ?? false;
  const genuineFpOk = loopM.comparison?.genuine_fp_ok ?? false;

  const gtestSeed = loopM.gtest_seed ?? 0;
  const trainSeed = loopM.train_seed ?? 0;

  return {
    family,
    gtestSeed,
    trainSeed,
    nExtra,
    capPct,
    catalogSolved: loopM.catalog_solved ?? false,
    apDelta,
    apVerdict,
    pass,
    genuineFpBefore,
    genuineFpAfter,
    genuineFpOk,
    barChart: {
      family,
      apDelta,
      verdict: apVerdict,
      rows: [
        { metric: "Binary AP", baseModel: baseBinaryAp, postFeedback: postBinaryAp },
        { metric: "Precision", baseModel: basePrecision, postFeedback: postPrecision },
        { metric: "Recall", baseModel: baseRecall, postFeedback: postRecall },
      ],
    },
    coEvolution: {
      family,
      gtestSeed,
      trainSeed,
      apDelta,
      pass,
      points: [
        { gen: "G0", evasion: g0Evasion, prAuc: g0PrAuc, genuineFpr: genuineFpBefore },
        { gen: "G1", evasion: g1Evasion, prAuc: g1PrAuc, genuineFpr: genuineFpAfter },
        { gen: "G2", evasion: null, prAuc: null, genuineFpr: null, projected: true },
      ],
    },
    ledger: {
      family,
      nExtra,
      capPct,
      g0: {
        binaryAp: baseBinaryAp,
        precision: basePrecision,
        recall: baseRecall,
        genuineFpr: genuineFpBefore,
        evasion: g0Evasion,
      },
      g1: {
        binaryAp: postBinaryAp,
        precision: postPrecision,
        recall: postRecall,
        genuineFpr: genuineFpAfter,
        prAuc: g1PrAuc,
        apDelta,
        evasion: g1Evasion,
      },
    },
  };
}
