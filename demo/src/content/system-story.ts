export interface StorySection {
  id: string;
  title: string;
  oneLine: string;
  body: string;
  bullets: string[];
  metricRef?: string;
}

export const SYSTEM_STORY: StorySection[] = [
  {
    id: "loop",
    title: "Closed loop",
    oneLine: "Identify → Generate → Defend → Loop M → back to Identify.",
    body:
      "AegisLoop is a lab rig for payment fraud: grounded threat intel becomes simulated UPI-like traffic, a champion detector scores it at a genuine-FPR operating point, and Loop M retrains on miss families without peeking at the grade world.",
    bullets: [
      "Identify: allowlisted OSINT → grounded specs → HITL approve → Atlas catalog.",
      "Generate: quiet world → typed injectors → fidelity gates → parquet export.",
      "Defend: causal tabular features + rules → HistGBM champion → Brake policy.",
      "Loop M: extra mix on train copy → new gtest seed → compare AP before/after.",
    ],
  },
  {
    id: "generate",
    title: "Generate — simulate payment traffic",
    oneLine: "Quiet legitimate world first; fraud injected with fidelity gates.",
    body:
      "We materialize ~2,400 customers over 90 days of legitimate spends, replay causal features, overlay mule / identity / APP / invoice families at ~2% fraud budget, then PSI-check amounts and fraud-rate bands before exporting ~400K-row ledgers.",
    bullets: [
      "Quiet world: no fraud until inject phase.",
      "Inject mix: fan-in mule, identity burst, APP session, invoice swap.",
      "Fidelity: PSI on amount/hour; anti-stub fraud-rate band.",
      "Export: allowlisted feature columns — labels never in X.",
    ],
  },
  {
    id: "histgbm",
    title: "HistGBM nested fit",
    oneLine: "Inner HGB picks threshold; outer HGB is the shipped champion.",
    body:
      "HistGradientBoostingClassifier trains on time-cut and entity-holdout folds. Inner fit learns a threshold on inner-val at target genuine FPR. Outer refit on full train uses the frozen threshold — eval fold never tunes OP.",
    bullets: [
      "Time cut: first 2/3 train calendar / last 1/3 eval.",
      "Entity holdout for mule payees — G2 protocol.",
      "Isotonic calibration + isolation forest kill-switch.",
      "Permutation importance + cluster bootstrap CI on inner-val.",
    ],
    metricRef: "champion_recall",
  },
  {
    id: "loopm",
    title: "Loop M feedback",
    oneLine: "Retrain on miss family; grade on new gtest seed 48.",
    body:
      "Miss family comes from diagnostic slice (gdev44), never gtest. Extra population at train_seed+10007 caps at 15% of train. Grading uses seed 48 — the loop cannot mark its own homework.",
    bullets: [
      "identity_burst AP 0.34 → 0.97 in champion pack.",
      "Genuine FPR guard ε=0.02 on gtest.",
      "catalog_solved: false — highlight returns to Identify.",
    ],
    metricRef: "loop_m",
  },
  {
    id: "champion",
    title: "Champion protocol",
    oneLine: "98.52% recall @ 0.032% genuine FPR on gtest-48.",
    body:
      "Threshold selected on inner-val at 0.1% FPR cap. Model v1-train-46__loopm-train after Loop M. Cold first-fit on seed-42 pop (~75% OP) is honest but not the hero metric.",
    bullets: [
      "Worlds: v1-train-46 train, v1-gtest-48 reported transfer.",
      "Frozen from internal_01pct_fpr_freeze.json.",
      "Prototype shows RECORDED champion — gates satisfied in lab artifacts.",
    ],
    metricRef: "champion_recall",
  },
  {
    id: "gates",
    title: "Seven honesty gates",
    oneLine: "G1–G7 lab rigor — causal features, temporal split, ablation.",
    body:
      "G1 causal features only. G2 temporal + entity holdout. G3 LLM ablation. G4 delayed labels. G5 baseline compare. G6 rollback. G7 coverage table. Netlify demo replays recorded packs; gates are documented not re-run live.",
    bullets: [
      "G1: past rows only in feature replay.",
      "G2: no random shuffle holdout.",
      "G3: APP flags ablation documented.",
      "G7: T01–T24 coverage chips on landscape.",
    ],
  },
];

export function storyForStage(stage: string): StorySection | undefined {
  const map: Record<string, string> = {
    identify: "loop",
    landscape: "loop",
    discover: "loop",
    review: "loop",
    generate: "generate",
    detection: "histgbm",
    interventions: "histgbm",
    feedback: "loopm",
    hyperparameters: "histgbm",
  };
  const id = map[stage];
  return SYSTEM_STORY.find((s) => s.id === id);
}
