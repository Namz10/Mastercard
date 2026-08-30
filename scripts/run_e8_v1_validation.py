#!/usr/bin/env python3
"""E8 — full v1 validation SOP (seeds 46/47/48). Appends to results-2.md."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results-2.md"
VAL_DIR = ROOT / "data" / "validation" / "v1"
MODELS = ROOT / "models"
RUNS = ROOT / "data" / "runs"
FEATURES = MODELS / "features.json"
FEATURES_WIP = MODELS / "features.wip.json"
FEATURES_V0 = MODELS / "features.v0.json"

TRAIN_RUN = "v1-train-46"
GDEV_RUN = "v1-gdev-47"
GTEST_RUN = "v1-gtest-48"
STAGE1_MODEL = TRAIN_RUN
STAGE2_MODEL = f"{TRAIN_RUN}-stage2"
LOOPM_MODEL = f"{TRAIN_RUN}__loopm-train"
SCALE = (2400, 120, 90)


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _append(section: str) -> None:
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(section)
        if not section.endswith("\n"):
            f.write("\n")


def _log(stage: str, body: str) -> None:
    print(f"\n=== {stage} ===\n{body}\n", flush=True)
    _append(f"\n<!-- updated {_ts()} -->\n{body}")


def _run_py(code: str, label: str) -> dict:
    t0 = time.perf_counter()
    env = {**dict(__import__("os").environ), "PYTHONPATH": str(ROOT), "PYTHONUNBUFFERED": "1"}
    proc = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed ({elapsed:.1f}s):\n{proc.stderr}\n{proc.stdout}")
    return {"stdout": proc.stdout.strip(), "elapsed_s": round(elapsed, 1)}


def activate_v1_recipe() -> None:
    if not FEATURES_WIP.is_file():
        raise FileNotFoundError(f"missing {FEATURES_WIP}")
    if FEATURES.is_file() and not FEATURES_V0.is_file():
        shutil.copy2(FEATURES, FEATURES_V0)
    shutil.copy2(FEATURES_WIP, FEATURES)


def pytest_gate() -> None:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "pytest",
            "tests/test_brake_invariants.py",
            "tests/test_post_g43_protocol.py",
            "tests/test_validation_protocol.py",
            "-q",
            "--tb=no",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"pytest gate failed:\n{proc.stderr}\n{proc.stdout}")
    _log("pytest gate", f"**Status:** passed ({elapsed:.0f}s)\n```\n{proc.stdout.strip()}\n```")


def generate_world(run_id: str, seed: int) -> dict:
    nc, nm, sd = SCALE
    code = f"""
from pathlib import Path
from apps.api.env import load_project_env
load_project_env()
from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.sim.runner import run_population
init_db()
seed_catalog(reset=True)
db = SessionLocal()
r = run_population(
    db, run_id={run_id!r}, n_customers={nc}, n_merchants={nm}, sim_days={sd},
    world_seed={seed}, pin=True, runs_dir=Path('data/runs'))
db.close()
import json
print(json.dumps({{
    'event_count': r['event_count'],
    'counts': r.get('counts_by_label_family', {{}}),
    'fidelity_pass': r.get('fidelity', {{}}).get('pass'),
}}))
"""
    out = _run_py(code, f"generate {run_id}")
    return json.loads(out["stdout"])


def main() -> None:
    VAL_DIR.mkdir(parents=True, exist_ok=True)
    activate_v1_recipe()
    pytest_gate()

    # Stage 0 — train world 46
    gen = generate_world(TRAIN_RUN, 46)
    _log(
        "Stage 0",
        f"**Command:** generate `{TRAIN_RUN}` seed 46\n"
        f"**event_count:** {gen['event_count']}\n"
        f"**fidelity:** {gen['fidelity_pass']}\n"
        f"**counts:** `{json.dumps(gen['counts'])}`",
    )

    # Stage 1 — fit
    code = f"""
from packages.eval.fit import fit_champion
import json
r = fit_champion({TRAIN_RUN!r}, world_seed=46, dest_run_id={STAGE1_MODEL!r})
m = r['metrics']
print(json.dumps({{
    'model_freeze_id': m.get('model_freeze_id'),
    'recipe_hash': m.get('recipe_hash'),
    'binary_ap': m.get('binary_ap'),
    'genuine_fp': m.get('genuine_fp'),
    'genuine_fp_over_eval': m.get('genuine_fp_over_eval'),
    'n_pos_by_fold': m.get('n_pos_by_fold'),
    'class_weight': m.get('class_weight'),
    'detect_thr': m.get('detect_thr'),
    'act_thr': m.get('act_thr'),
    'n_train': m.get('n_train'),
    'n_eval': m.get('n_eval'),
    'ap_by_family': m.get('ap_by_family'),
    'not_comparable': m.get('not_comparable'),
    'without_stamps': m.get('app_ablation', {{}}).get('without_stamps'),
    'action_hist': r.get('action_histogram'),
}}))
"""
    fit = json.loads(_run_py(code, "fit stage1")["stdout"])
    (VAL_DIR / "stage1_fit.json").write_text(json.dumps(fit, indent=2), encoding="utf-8")
    _log("Stage 1", f"**fit_champion** `{STAGE1_MODEL}`\n```json\n{json.dumps(fit, indent=2)}\n```")

    # Stage 1b — gdev 47 + family pick
    gdev = generate_world(GDEV_RUN, 47)
    code = f"""
from packages.eval.fit import score_run
import json
s = score_run({GDEV_RUN!r}, model_run_id={STAGE1_MODEL!r}, all_rows=True)
m = s['metrics']
print(json.dumps({{'ap_by_family': m['ap_by_family'], 'n_pos': m['n_pos'], 'not_comparable': m['not_comparable']}}))
"""
    gdev_score = json.loads(_run_py(code, "gdev score")["stdout"])
    pick = None
    best_ap = float("inf")
    for fam, ap in gdev_score["ap_by_family"].items():
        if fam == "normal":
            continue
        n = int(gdev_score["n_pos"].get(fam, 0))
        if n < 30:
            continue
        try:
            ap_f = float(ap)
        except (TypeError, ValueError):
            continue
        if ap_f < best_ap:
            best_ap = ap_f
            pick = fam
    if not pick:
        raise RuntimeError(f"no Loop M family with n_pos>=30 on {GDEV_RUN}")
    pick_doc = {
        "run_id": TRAIN_RUN,
        "gdev_run_id": GDEV_RUN,
        "target_family": pick,
        "gdev_ap": gdev_score["ap_by_family"].get(pick),
        "gdev_n_pos": gdev_score["n_pos"].get(pick),
        "picked_at": _ts(),
    }
    (VAL_DIR / "loop_m_family_pick.json").write_text(json.dumps(pick_doc, indent=2), encoding="utf-8")
    _log(
        "Stage 1b",
        f"**G-dev** `{GDEV_RUN}` event_count={gdev['event_count']}\n"
        f"**family pick:** `{pick}`\n```json\n{json.dumps(pick_doc, indent=2)}\n```",
    )

    # n_pos proxy (mule on train eval fold)
    mule_n = int(fit.get("n_pos_by_fold", {}).get("eval", {}).get("mule", fit.get("n_pos", {}).get("mule", 0)))
    npos = {"mule_eval_n_pos": mule_n, "comparable": mule_n >= 30, "action": "proceed" if mule_n >= 15 else "fail_e1"}
    (VAL_DIR / "npos_proxy.json").write_text(json.dumps(npos, indent=2), encoding="utf-8")

    # Stage 3 Loop M (before photography)
    code = f"""
from packages.eval.loop_m import run_loop_m
import json
body = run_loop_m(
    {TRAIN_RUN!r}, {pick!r},
    train_seed=46, gtest_seed=48,
    family_chosen_from_slice='gdev44',
    n_customers={SCALE[0]}, n_merchants={SCALE[1]}, sim_days={SCALE[2]}, pin=True,
)
print(json.dumps(body, default=str))
"""
    loop_m = json.loads(_run_py(code, "loop m")["stdout"])
    (VAL_DIR / "loop_m_result.json").write_text(json.dumps(loop_m, indent=2), encoding="utf-8")
    _log("Stage 3 Loop M", f"```json\n{json.dumps(loop_m, indent=2)[:4000]}\n```")

    # Stage 2 Optuna
    code = f"""
from packages.eval.fit import tune_champion
import json
r = tune_champion({TRAIN_RUN!r}, world_seed=46, dest_run_id={STAGE2_MODEL!r})
print(json.dumps(r, default=str))
"""
    tune = json.loads(_run_py(code, "optuna")["stdout"])
    trials_path = MODELS / STAGE2_MODEL / "trials.json"
    tune_summary = {"tune": tune, "trials_file": str(trials_path) if trials_path.is_file() else None}
    (VAL_DIR / "tune_summary.json").write_text(json.dumps(tune_summary, indent=2), encoding="utf-8")
    _log("Stage 2 Optuna", f"```json\n{json.dumps(tune_summary, indent=2)}\n```")

    # Stage 3b Loop T
    code = f"""
from packages.eval.loop_t import mine_fn_rules
import json
res = mine_fn_rules({STAGE1_MODEL!r}, {GDEV_RUN!r}, {pick!r})
print(json.dumps(res, default=str))
"""
    loop_t = json.loads(_run_py(code, "loop t")["stdout"])
    (VAL_DIR / "loop_t_result.json").write_text(json.dumps(loop_t, indent=2), encoding="utf-8")
    _log("Stage 3b Loop T", f"```json\n{json.dumps(loop_t, indent=2)}\n```")

    # Generate gtest 48
    gtest_gen = generate_world(GTEST_RUN, 48)
    _log("Photography prep", f"**Generated** `{GTEST_RUN}` events={gtest_gen['event_count']}")

    # Photography Day
    photos = {}
    for label, mid in [
        ("stage1", STAGE1_MODEL),
        ("stage2", STAGE2_MODEL),
        ("loopm", LOOPM_MODEL),
    ]:
        code = f"""
from packages.eval.fit import score_run
import json
s = score_run({GTEST_RUN!r}, model_run_id={mid!r}, all_rows=True)
m = s['metrics']
print(json.dumps({{
    'model_run_id': {mid!r},
    'model_freeze_id': s.get('model_freeze_id'),
    'binary_ap': m.get('binary_ap'),
    'genuine_fp': m.get('genuine_fp'),
    'genuine_fp_over_eval': m.get('genuine_fp_over_eval'),
    'precision_at_op': m.get('precision_at_op'),
    'recall_at_op': m.get('recall_at_op'),
    'ap_by_family': m.get('ap_by_family'),
    'n_pos': m.get('n_pos'),
    'not_comparable': m.get('not_comparable'),
    'without_stamps': m.get('app_ablation', {{}}).get('without_stamps'),
    'action_histogram': s.get('action_histogram'),
    'detect_thr': m.get('detect_thr'),
    'act_thr': m.get('act_thr'),
}}))
"""
        photos[label] = json.loads(_run_py(code, f"photo {label}")["stdout"])

    (VAL_DIR / "photography_day.json").write_text(json.dumps(photos, indent=2), encoding="utf-8")
    mule_gtest = int(photos["stage1"]["n_pos"].get("mule", 0))
    npos_gate = {
        "mule_n_pos": mule_gtest,
        "comparable": mule_gtest >= 30,
        "world_seed": 48,
        "run_id": GTEST_RUN,
    }
    (VAL_DIR / "npos_gate.json").write_text(json.dumps(npos_gate, indent=2), encoding="utf-8")

    delta = {
        "binary_ap_delta": photos["stage2"]["binary_ap"] - photos["stage1"]["binary_ap"],
        "genuine_fp_delta_pp": (photos["stage2"]["genuine_fp"] - photos["stage1"]["genuine_fp"]) * 100,
        "verdict": "stage2_fp_worse" if photos["stage2"]["genuine_fp"] > photos["stage1"]["genuine_fp"] else "stage2_ok",
    }
    (VAL_DIR / "delta_vs_stage1.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")

    _log(
        "Photography Day",
        f"**World:** `{GTEST_RUN}` seed 48\n```json\n{json.dumps(photos, indent=2)[:8000]}\n```\n"
        f"**npos_gate:** `{json.dumps(npos_gate)}`\n**delta:** `{json.dumps(delta)}`",
    )

    print("\nE8 complete. See results-2.md and data/validation/v1/", flush=True)


if __name__ == "__main__":
    main()
