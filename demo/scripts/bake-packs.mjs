#!/usr/bin/env node
/**
 * Bake static packs for Netlify booth demo.
 * Run from repo root: node demo/scripts/bake-packs.mjs
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import yaml from "js-yaml";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEMO_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(DEMO_ROOT, "..");
const PACKS = path.join(DEMO_ROOT, "public", "packs");
const DATA = path.join(REPO_ROOT, "data");
const VALIDATION = path.join(DATA, "validation", "v1");

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function writeJson(name, obj) {
  const out = path.join(PACKS, name);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(obj, null, 2));
  console.log("wrote", out);
}

function readTpr(entry) {
  if (entry == null) return null;
  if (typeof entry === "number") return entry;
  if (typeof entry === "object" && "tpr" in entry) return entry.tpr;
  return null;
}

function freezeScore() {
  const freeze = readJson(path.join(VALIDATION, "internal_01pct_fpr_freeze.json"));
  const op = freeze.frozen_operating_point;
  const modelRunId = freeze.model_run_id ?? "v1-train-46__loopm-train";

  const tprAtFpr = {};
  const paretoPath = path.join(VALIDATION, "pareto_gtest48.json");
  if (fs.existsSync(paretoPath)) {
    const paretoDoc = readJson(paretoPath);
    const loopm = paretoDoc.models?.LoopM?.pareto ?? {};
    for (const [key, entry] of Object.entries(loopm)) {
      if (typeof entry !== "object" || !entry) continue;
      const tpr = readTpr(entry.tpr);
      if (tpr != null) tprAtFpr[key] = { tpr, fpr_target: Number(key) };
    }
  }

  const genuinePath = path.join(VALIDATION, "pareto_genuine_fpr.json");
  if (fs.existsSync(genuinePath)) {
    const genuineDoc = readJson(genuinePath);
    const loopmG =
      genuineDoc.worlds?.["v1-gtest-48"]?.LoopM?.envelope ?? {};
    for (const [key, entry] of Object.entries(loopmG)) {
      if (typeof entry !== "object" || !entry) continue;
      const recallPt = entry.recall;
      if (recallPt != null) {
        tprAtFpr[key] = { tpr: Number(recallPt), fpr_target: Number(key) };
      }
    }
  }

  const gf = Number(op.genuine_fp);
  const recall = Number(op.recall_at_op);
  tprAtFpr[`${gf.toPrecision(6)}`] = { tpr: recall, fpr_target: gf };

  const refRecall = freeze.acceptance?.reference_posthoc_pareto_recall_01pct_g48;
  if (refRecall != null) {
    tprAtFpr["0.001"] = { tpr: Number(refRecall), fpr_target: 0.001 };
  }

  const nPos = op.n_pos ?? {};
  const nEval = Object.values(nPos).reduce((a, v) => a + Number(v), 0);
  const cm = op.confusion_matrix ?? {};
  const confusion =
    typeof cm === "object"
      ? [cm.tn ?? 0, cm.fp ?? 0, cm.fn ?? 0, cm.tp ?? 0]
      : cm;

  const apByFamily = op.ap_by_family ?? {};
  const metrics = {
    pass: true,
    n_eval: nEval,
    ap_by_family: Object.fromEntries(
      Object.entries(apByFamily).map(([k, v]) => [k, { ap: v }]),
    ),
    tpr_at_fpr: tprAtFpr,
    genuine_fp: gf,
    f1_at_op: 0,
    precision_at_op: Number(op.precision_at_op ?? 0.9857),
    recall_at_op: recall,
    binary_ap: Number(op.binary_ap ?? 0.9985),
    confusion_matrix: confusion,
    op_threshold: Number(op.detect_thr ?? 0.915),
    recipe_hash: "frozen",
    model_freeze_id: "frozen",
    top_features: freeze.top_features ?? [],
    n_pos: nPos,
  };

  return {
    run_id: freeze.eval_run_id ?? "v1-gtest-48",
    model_run_id: modelRunId,
    metrics,
    action_histogram: op.action_histogram ?? {},
    split: "gtest",
    recipe_hash: "frozen",
    model_freeze_id: "frozen",
    frozen: true,
  };
}

function coverageStatus(row) {
  const mode = row.generate_mode ?? "generate";
  const feats = row.features_expected ?? [];
  const name = (row.name ?? "").toLowerCase();
  if (mode === "case_only") return "case_only";
  if (mode === "named_gap") return "named_gap";
  if (row.technique_id === "T09" || name.includes("deepfake")) return "named_gap";
  if (mode === "generate" && feats.length > 0) return "live_rule";
  return "draft_rule";
}

function buildCatalogPacks() {
  const seedPath = path.join(DATA, "catalog", "seed.yaml");
  const rows = yaml.load(fs.readFileSync(seedPath, "utf-8"));
  const categories = {};
  const cells = [];
  const statusCounts = {};

  for (const row of rows) {
    const tid = row.technique_id;
    const cat = Number(row.category ?? 1);
    categories[cat] = categories[cat] ?? [];
    const chip = {
      vector_id: row.vector_id,
      technique_id: tid,
      name: row.name,
      category: cat,
      confidence_level: row.confidence_level,
      source_tier: row.source_tier,
    };
    let group = categories[cat].find((g) => g.technique_id === tid);
    if (!group) {
      group = {
        technique_id: tid,
        name: row.name,
        status: row.status ?? "open",
        generate_mode: row.generate_mode,
        confidence_level: row.confidence_level,
        source_tier: row.source_tier,
        chips: [],
        variants: 0,
      };
      categories[cat].push(group);
    }
    group.chips.push(chip);
    group.variants = group.chips.length;

    const cov = coverageStatus(row);
    statusCounts[cov] = (statusCounts[cov] ?? 0) + 1;
    cells.push({
      technique_id: tid,
      vector_id: row.vector_id,
      name: row.name,
      coverage_status: cov,
      generate_mode: row.generate_mode,
      live_rule_ids: cov === "live_rule" ? [`rule-${tid}`] : [],
      named_gap_reason: cov === "named_gap" ? "Offline or deepfake — case study only" : null,
      draft_rule: cov === "draft_rule" ? { id: `draft-${tid}` } : null,
      features_expected: row.features_expected ?? [],
      scout_topic_hint: row.novelty_notes ?? null,
    });
  }

  writeJson("threat-map.json", {
    categories,
    technique_count: cells.length,
  });

  writeJson("coverage-map.json", {
    technique_count: cells.length,
    cells,
    status_counts: statusCounts,
    scout_topics_for_gaps: ["deepfake vkyc", "offline cash mule"],
  });
}

function buildHitl() {
  writeJson("hitl-queue.json", {
    items: [
      {
        id: "hitl-t13",
        technique_id: "T13",
        vector_id: "t13-upi-impersonation-app",
        name: "UPI impersonation APP",
        confidence: 0.92,
        source_url: "https://www.rbi.org.in/",
        rationale: "RBI alert on impersonation scams via UPI collect requests.",
      },
      {
        id: "hitl-t11",
        technique_id: "T11",
        vector_id: "t11-identity-farming",
        name: "Identity farming burst",
        confidence: 0.88,
        source_url: "https://www.fincen.gov/",
        rationale: "FinCEN pattern: synthetic identity burst before cash-out.",
      },
      {
        id: "hitl-t09",
        technique_id: "T09",
        vector_id: "t09-deepfake-vkyc",
        name: "Deepfake vKYC bypass",
        confidence: 0.75,
        source_url: "https://www.fincen.gov/",
        rationale: "Named gap — documented case, not simulatable live rule.",
      },
    ],
  });
}

function narrate(verb, body, defaults) {
  return {
    now: defaults?.now ?? `${verb}: ${body}`,
    why: defaults?.why ?? "Lab protocol step — see How it works.",
    happening: defaults?.happening ?? body,
    next: defaults?.next,
    visual: defaults?.visual,
  };
}

function buildIdentifyTimeline() {
  const fixtures = path.join(DATA, "osint", "fixtures");
  const urls = [];
  if (fs.existsSync(fixtures)) {
    for (const p of fs.readdirSync(fixtures).sort().slice(0, 6)) {
      if (!p.endsWith(".json")) continue;
      try {
        const doc = readJson(path.join(fixtures, p));
        urls.push(String(doc.url ?? doc.source_url ?? p));
      } catch {
        urls.push(p);
      }
    }
  }
  if (!urls.length) urls.push("fincen.gov", "rbi.org.in", "reuters.com");

  const events = [
    { t: 0, verb: "COLLECT", body: "Collect started", status: "started", ...narrate("COLLECT", "Collect started", { now: "Scanning allowlisted OSINT sources", why: "Identify only uses vetted URLs — not open web search.", happening: "FinCEN, RBI, IOC feeds" }) },
    { t: 800, verb: "COLLECT", body: `Source ${urls[0]}`, status: "ok", artifacts: { urls: [urls[0]] }, ...narrate("COLLECT", urls[0], { now: `Reading ${urls[0]}` }) },
    { t: 3000, verb: "COLLECT", body: `Source ${urls[1] ?? urls[0]}`, status: "ok", ...narrate("COLLECT", urls[1] ?? urls[0]) },
    { t: 6000, verb: "EXTRACT", body: "Reading articles", status: "ok", ...narrate("EXTRACT", "Reading articles", { now: "Extracting attack phrases", happening: "NER + citation spans" }) },
    { t: 9000, verb: "RANK", body: "Ranking sources", status: "ok", ...narrate("RANK", "Ranking sources", { now: "Ranking by tier and corroboration" }) },
    { t: 11000, verb: "GROUND", body: "Matching to the catalog", status: "ok", ...narrate("GROUND", "Matching to the catalog", { now: "Grounding to T01–T24 atlas", visual: "customers" }) },
    { t: 14000, verb: "PROPOSE", body: "Proposing attacks for review", status: "ok", ...narrate("PROPOSE", "Proposing attacks", { now: "Three HITL candidates ready" }) },
    { t: 15000, verb: "REPLAY", body: "Playback complete", status: "done", result: { run_id: "recorded-identify", candidate_urls: urls }, ...narrate("REPLAY", "Complete", { now: "Discover complete — review queue open" }) },
  ];
  writeJson("timelines/identify.json", { events });
}

function buildGenerateTimeline() {
  const quietTicks = [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400];
  const events = [
    { t: 0, verb: "COMMIT", body: "Build quiet payment world · 2400 customers · 90d", status: "started", ...narrate("COMMIT", "Quiet world", { now: "Building quiet payment world", why: "Legitimate traffic first — fraud injected later.", visual: "customers" }) },
  ];
  for (const n of quietTicks) {
    events.push({
      t: 500 + n * 40,
      verb: "COMMIT",
      body: `Quiet traffic — ${n * 100} of 2400 customers`,
      status: "progress",
      artifacts: { customers: n * 100, total: 2400 },
      ...narrate("COMMIT", `Customer ${n * 100}`, { now: `Materializing legitimate spends — ${n * 100} of 2400 customers`, happening: "Fraud is not in the ledger yet.", visual: "customers" }),
    });
  }
  events.push({
    t: 12000,
    verb: "COMMIT",
    body: "390,411 quiet events materialized",
    status: "ok",
    artifacts: { events: 390411 },
    ...narrate("COMMIT", "390K events", { now: "390,411 quiet events on ledger", visual: "events" }),
  });
  events.push({
    t: 14000,
    verb: "COMMIT",
    body: "Replaying causal features on quiet ledger",
    status: "progress",
    ...narrate("COMMIT", "Feature replay", { now: "Replaying causal features on 390K rows", why: "G1 — past rows only, no label leakage.", happening: "Causal feature replay" }),
  });
  const injects = [
    { family: "mule", count: 3191, body: "Layer mule fan-in and cash-out paths" },
    { family: "identity_burst", count: 1549, body: "Identity burst overlay" },
    { family: "ato", count: 398, body: "Account takeover sessions" },
    { family: "app_fraud", count: 1586, body: "APP impersonation sessions" },
    { family: "invoice_fraud", count: 760, body: "Invoice beneficiary swap" },
  ];
  let t = 16000;
  for (const inj of injects) {
    events.push({
      t,
      verb: "INJECT",
      body: inj.body,
      status: "ok",
      artifacts: { family: inj.family, count: inj.count },
      ...narrate("INJECT", inj.body, { now: `Overlaying ${inj.family} — ${inj.count} rows`, visual: "families" }),
    });
    t += 2500;
  }
  events.push({
    t,
    verb: "FIDELITY",
    body: "PSI amount 0.05 · fraud rate 1.88%",
    status: "ok",
    ...narrate("FIDELITY", "PSI pass", { now: "Fidelity gates pass — priors match lab band", why: "Anti-stub: PSI + fraud-rate band." }),
  });
  t += 2000;
  events.push({
    t,
    verb: "COMMIT",
    body: "Export train/split parquet — allowlisted columns only",
    status: "progress",
    ...narrate("COMMIT", "Parquet", { now: "Writing parquet — labels never in X", happening: "Allowlisted feature columns only" }),
  });
  t += 3000;
  const generateResult = {
    run_id: "demo-pop-v1",
    seed: 42,
    scale: "full",
    fidelity_pass: true,
    fidelity_reasons: [],
    event_count: 398431,
    family_counts: {
      mule: 3191,
      identity_burst: 1549,
      ato: 398,
      app_fraud: 1586,
      invoice_fraud: 760,
    },
    mule_fan_in: 18,
  };
  events.push({
    t,
    verb: "COMMIT",
    body: "Population committed — 398,431 events",
    status: "done",
    result: generateResult,
    ...narrate("COMMIT", "Done", { now: "Generate complete — 398,431 events", next: "Defend fit on train fold" }),
  });
  writeJson("timelines/generate.json", { events });
  writeJson("generate-result.json", generateResult);
}

function buildFitTimeline() {
  const stages = [
    { key: "load_parquet", dur: 3000, body: "Load holdout parquet" },
    { key: "attach_rule_bits", dur: 2000, body: "Attach policy rule bits" },
    { key: "assign_folds", dur: 2500, body: "Assign train and holdout folds" },
    { key: "encode_features", dur: 2000, body: "Encode features" },
    { key: "inner_hgb", dur: 8000, body: "Train detector", visual: "hgb" },
    { key: "inner_val_threshold", dur: 4000, body: "Choose validation threshold" },
    { key: "isolation_forest", dur: 5000, body: "Isolation forest" },
    { key: "outer_hgb", dur: 8000, body: "Outer model", visual: "hgb" },
    { key: "outer_eval_calibration", dur: 4000, body: "Calibrate scores" },
    { key: "app_ablation", dur: 3000, body: "APP fraud ablation check" },
    { key: "permutation_importance", dur: 18000, body: "Which features moved the score" },
    { key: "bootstrap_ci", dur: 12000, body: "Checking stability on holdout", visual: "bootstrap" },
    { key: "brake_hist", dur: 3000, body: "Policy histogram at the operating point" },
    { key: "persist", dur: 2000, body: "Persist champion model" },
  ];
  const narrMap = {
    inner_hgb: { now: "Training inner HistGBM on inner_fit only", why: "Threshold model — not the shipped champion yet.", happening: "HistGradientBoostingClassifier fit" },
    outer_hgb: { now: "Refit outer HGB on full train", why: "Threshold already frozen — no eval peek.", happening: "Champion model training" },
    permutation_importance: { now: "Permutation importance — shuffle features", why: "Which columns moved neg-log-loss.", happening: "10 repeats per feature" },
    bootstrap_ci: { now: "Cluster bootstrap by payee/payer", why: "Stability bands on AP — lab rigor.", happening: "200 resamples per family", visual: "bootstrap" },
    assign_folds: { now: "Time cut + entity holdout folds", why: "G2 — no random shuffle holdout.", happening: "First 2/3 train calendar / entity holdout" },
  };
  let t = 0;
  const events = [];
  const score = freezeScore();
  for (const stage of stages) {
    const n = narrMap[stage.key] ?? narrate("FIT", stage.body);
    events.push({
      t,
      verb: "FIT",
      body: stage.body,
      status: "progress",
      ...n,
      visual: stage.visual ?? n.visual,
    });
    if (stage.key === "bootstrap_ci") {
      for (const [i, fam] of ["mule", "app_fraud", "identity_burst", "ato", "invoice_fraud"].entries()) {
        events.push({
          t: t + 1000 + i * 800,
          verb: "FIT",
          body: `bootstrap_ci family=${fam} resample ${25 + i * 35}/200`,
          status: "progress",
          ...narrate("FIT", fam, { now: `Bootstrap ${fam} — resample ${25 + i * 35}/200`, visual: "bootstrap" }),
          artifacts: { family: fam, resample: 25 + i * 35, total: 200 },
        });
      }
    }
    t += stage.dur;
  }
  events.push({
    t,
    verb: "FIT",
    body: "Champion fit complete",
    status: "done",
    result: score,
    ...narrate("FIT", "Done", { now: "Champion scored — recall @ genuine FPR", next: "Interventions brake rail" }),
  });
  writeJson("timelines/fit.json", { events });
  writeJson("score-champion.json", score);
}

function buildLoopTimeline() {
  const loopPath = path.join(VALIDATION, "loop_m_result.json");
  const loopBase = fs.existsSync(loopPath)
    ? readJson(loopPath)
    : readJson(path.join(DATA, "validation", "stage3", "loop_m_result.json"));

  const freeze = readJson(path.join(VALIDATION, "internal_01pct_fpr_freeze.json"));
  const op = freeze.frozen_operating_point;
  const comp = loopBase.comparison ?? {};

  function metricsFromComparison(before) {
    const apByFamily = {};
    if (before) {
      for (const [k, v] of Object.entries(op.ap_by_family ?? {})) {
        if (k === loopBase.miss_family) {
          apByFamily[k] = { ap: comp.ap_before ?? 0.34 };
        } else {
          apByFamily[k] = { ap: v };
        }
      }
    } else {
      for (const [k, v] of Object.entries(op.ap_by_family ?? {})) {
        if (k === loopBase.miss_family) {
          apByFamily[k] = { ap: comp.ap_after ?? 0.97 };
        } else {
          apByFamily[k] = { ap: v };
        }
      }
    }
    const gf = before ? comp.genuine_fp_before ?? 0.088 : comp.genuine_fp_after ?? 0.081;
    const recall = before ? 0.72 : Number(op.recall_at_op);
    return {
      pass: true,
      n_eval: 394954,
      ap_by_family: apByFamily,
      tpr_at_fpr: freezeScore().metrics.tpr_at_fpr,
      genuine_fp: gf,
      recall_at_op: recall,
      precision_at_op: Number(op.precision_at_op ?? 0.98),
      binary_ap: Number(op.binary_ap ?? 0.99),
      confusion_matrix: op.confusion_matrix,
      op_threshold: Number(op.detect_thr),
      recipe_hash: "frozen",
      model_freeze_id: "frozen",
      n_pos: comp.n_pos_before ?? op.n_pos,
    };
  }

  const gtestBefore = metricsFromComparison(true);
  const gtestAfter = metricsFromComparison(false);
  gtestAfter.recall_at_op = Number(op.recall_at_op);
  gtestAfter.genuine_fp = Number(op.genuine_fp);

  const loopChampion = {
    ...loopBase,
    model_run_id_before: loopBase.model_run_id_before ?? "v1-train-46",
    model_run_id_after: loopBase.model_run_id_after ?? "v1-train-46__loopm-train",
    metrics: {
      pass: true,
      protocol: "g_test_new_seed",
      gtest_before: gtestBefore,
      gtest_after: gtestAfter,
    },
  };
  writeJson("loop-m-champion.json", loopChampion);

  const miss = loopBase.miss_family ?? "identity_burst";
  let t = 0;
  const events = [
    { t, verb: "LOOP", body: `Miss family: ${miss}`, status: "started", ...narrate("LOOP", miss, { now: `Loop M — miss family ${miss}`, why: "Chosen from diagnostic slice — not gtest." }) },
    { t: 3000, verb: "LOOP", body: "Extra population seed train+10007", status: "progress", ...narrate("LOOP", "Extra mix", { now: "Generating extra rows for miss family only", happening: "Cap 15% of train" }) },
    { t: 8000, verb: "LOOP", body: "New gtest world seed 48", status: "progress", ...narrate("LOOP", "gtest 48", { now: "New gtest population — seed 48", why: "Loop cannot mark its own homework." }) },
    { t: 14000, verb: "LOOP", body: "Refit parent model", status: "progress", ...narrate("LOOP", "Refit", { now: "Refitting on augmented train copy" }) },
    { t: 20000, verb: "LOOP", body: "Score gtest before/after", status: "progress", ...narrate("LOOP", "Grade", { now: "Grading on locked gtest — apples to apples" }) },
    {
      t: 24000,
      verb: "LOOP",
      body: "Loop M complete",
      status: "done",
      result: loopChampion,
      ...narrate("LOOP", "Done", { now: `${miss} AP improved on gtest`, next: "Optional Optuna tune" }),
    },
  ];
  writeJson("timelines/loop-m.json", { events });
}

function buildTuneTimeline() {
  const score = freezeScore();
  const tuned = structuredClone(score);
  tuned.model_run_id = `${score.model_run_id}-tuned`;
  tuned.metrics.recall_at_op = Math.min(0.99, score.metrics.recall_at_op + 0.002);
  writeJson("score-tuned.json", tuned);

  const events = [
    { t: 0, verb: "TUNE", body: "Optuna search on inner-val only", status: "started", ...narrate("TUNE", "Optuna", { now: "Hyperparameter search — inner-val only", why: "Holdout frozen; skip if too few fraud rows." }) },
    { t: 4000, verb: "TUNE", body: "Trial 3 of 12 — learning_rate 0.08", status: "progress", artifacts: { trial: 3, total: 12 } },
    { t: 8000, verb: "TUNE", body: "Trial 8 of 12 — max_depth 4", status: "progress", artifacts: { trial: 8, total: 12 } },
    { t: 12000, verb: "TUNE", body: "Tune complete", status: "done", result: { tune: { trials: 12, best: tuned.metrics.recall_at_op }, score: tuned }, ...narrate("TUNE", "Done", { now: "Tune complete — compare base / feedback / tuned" }) },
  ];
  writeJson("timelines/tune.json", { events });
}

function buildExplain() {
  const freeze = readJson(path.join(VALIDATION, "internal_01pct_fpr_freeze.json"));
  writeJson("explain.json", {
    top_features: freeze.top_features ?? ["rail", "fan_in_1h", "account_age_days", "mule_account_age_days", "rule__mule-fan-in-burst"],
    importances_mean: freeze.importances_mean ?? {},
    bootstrap_ci: freeze.bootstrap_ci ?? {},
    champion_recall: freeze.frozen_operating_point?.recall_at_op,
    champion_genuine_fp: freeze.frozen_operating_point?.genuine_fp,
  });
}

function main() {
  fs.mkdirSync(PACKS, { recursive: true });
  buildCatalogPacks();
  buildHitl();
  buildIdentifyTimeline();
  buildGenerateTimeline();
  buildFitTimeline();
  buildLoopTimeline();
  buildTuneTimeline();
  buildExplain();
  console.log("Bake complete.");
}

main();
