"""SAML-D FeatureComputer replay adapter (Stage 4).

Naive reindex of the 12 CSV headers onto the lab champion is invalid.
Replay G(t−) via FeatureComputer; APP/invoice/device stamps stay false.
Never map rows to app_fraud or ato.
"""

from __future__ import annotations

import csv
import gc
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_score, recall_score

from packages.eval.fit import (
    CAT_COLS,
    _apply_pmap_calibrators,
    _attach_rule_bits,
    _encode,
    _fraud_score,
    _proba_map,
    _tpr_at_fpr,
    load_champion,
)
from packages.policy.rules import load_v0_rules
from packages.sim.export import TRAIN_ALLOWLIST
from packages.sim.features import FeatureComputer
from packages.sim.ledger import LABEL_FAMILIES, empty_app_flags

CSV_HEADERS = (
    "Time",
    "Date",
    "Sender_account",
    "Receiver_account",
    "Amount",
    "Payment_currency",
    "Received_currency",
    "Sender_bank_location",
    "Receiver_bank_location",
    "Payment_type",
    "Is_laundering",
    "Laundering_type",
)

FORBIDDEN_FAMILIES = frozenset({"app_fraud", "ato"})
DEFAULT_CSV = Path("data/external/SAML-D.csv")
CSV_CANDIDATES = (
    DEFAULT_CSV,
    Path("data/externals/SAML-D.csv"),
)
KYC_DEFAULT = "tier2"
RAIL_ANALOGUE = "upi_like"

# ICEBE 2023 prose names, normalized. Live CSV may use underscores; map_label_family
# matches after _norm_type. Over-invoicing is the only invoice analog.
_MULE_TYPES = frozenset(
    {
        "fan out",
        "fan in",
        "cycle",
        "bipartite",
        "stacked bipartite",
        "scatter gather",
        "gather scatter",
        "layered fan in",
        "layered fan out",
        "structuring",
        "smurfing",
        "deposit send",
        "cash withdrawal",
    }
)
_INVOICE_TYPES = frozenset({"over invoicing", "overinvoicing"})
_UNMAPPED_TYPES = frozenset(
    {
        "single large",
        "single large transaction",
        "behaviour change 1",
        "behavioural change 1",
        "behaviour change 2",
        "behavioural change 2",
        "behavior change 1",
        "behavioral change 2",
    }
)


def _norm_type(value: Any) -> str:
    s = re.sub(r"[\s_\-/]+", " ", str(value or "").strip().lower())
    return s.strip()


def map_label_family(is_laundering: Any, laundering_type: Any) -> str:
    """Map SAML-D labels. Never returns app_fraud or ato."""
    try:
        flagged = int(is_laundering) == 1
    except (TypeError, ValueError):
        flagged = bool(is_laundering)
    if not flagged:
        return "normal"
    t = _norm_type(laundering_type)
    if t in _INVOICE_TYPES:
        fam = "invoice_fraud"
    elif t in _MULE_TYPES:
        fam = "mule"
    else:
        fam = "unmapped"
    if fam in FORBIDDEN_FAMILIES:
        raise AssertionError(f"SAML-D mapper produced forbidden family {fam}")
    return fam


def parse_event_ts(date_val: Any, time_val: Any) -> datetime:
    date_s = str(date_val).strip()
    time_s = str(time_val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            ts = datetime.strptime(f"{date_s} {time_s}", fmt)
            return ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(date_s, fmt)
            hms = time_s if ":" in time_s else "00:00:00"
            ts = datetime.strptime(f"{d.date().isoformat()} {hms}", "%Y-%m-%d %H:%M:%S")
            return ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unparseable SAML-D Date/Time: {date_val!r} {time_val!r}")


def assert_csv_headers(columns: list[str] | pd.Index) -> None:
    cols = set(str(c) for c in columns)
    missing = [h for h in CSV_HEADERS if h not in cols]
    if missing:
        raise ValueError(
            f"SAML-D CSV missing required headers {missing}. "
            "Use Is_laundering / Laundering_type, not paper prose Is Suspicious / Type."
        )
    banned = {"Is_Suspicious", "Is Suspicious", "Type"} & cols
    if "Is_laundering" not in cols:
        raise ValueError("SAML-D adapter requires Is_laundering (not Is_Suspicious)")


def _amount_minor(amount: Any) -> int:
    try:
        return max(0, int(round(float(amount) * 100)))
    except (TypeError, ValueError):
        return 0


def _feature_row(snap: dict[str, Any], fam: str, is_l: int, ltype: str) -> dict[str, Any]:
    return {
        "rail": RAIL_ANALOGUE,
        "kyc_tier": KYC_DEFAULT,
        "account_age_days": int(snap.get("account_age_days", 0) or 0),
        "payee_history_count": int(snap.get("payee_history_count", 0) or 0),
        "amount_vs_p30": float(snap.get("amount_vs_p30", 0) or 0),
        "fan_in_1h": int(snap.get("fan_in_1h", 0) or 0),
        "fan_out_1h": int(snap.get("fan_out_1h", 0) or 0),
        "fan_in_unique_payers_1h": int(snap.get("fan_in_unique_payers_1h", 0) or 0),
        "is_new_payee": int(snap.get("is_new_payee", 0) or 0),
        "is_new_device": 0,
        "burst_velocity": float(snap.get("burst_velocity", 0) or 0),
        "fan_in_24h": int(snap.get("fan_in_24h", 0) or 0),
        "fan_out_24h": int(snap.get("fan_out_24h", 0) or 0),
        "fan_in_unique_payers_24h": int(snap.get("fan_in_unique_payers_24h", 0) or 0),
        "txn_velocity_24h": int(snap.get("txn_velocity_24h", 0) or 0),
        "hours_since_prev_txn": float(snap.get("hours_since_prev_txn", 168.0) or 168.0),
        "hours_since_payee": float(snap.get("hours_since_payee", 168.0) or 168.0),
        "amount_vs_7d_mean": float(snap.get("amount_vs_7d_mean", 0) or 0),
        "unique_payees_7d": int(snap.get("unique_payees_7d", 0) or 0),
        "payee_fan_out_1h": int(snap.get("payee_fan_out_1h", 0) or 0),
        "in_out_asymmetry_24h": float(snap.get("in_out_asymmetry_24h", 0) or 0),
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "urgency_pressure": 0.0,
        "beneficiary_changed": False,
        "gstin_checksum_ok": False,
        "lookalike_domain_flag": False,
        "label_family": fam if fam in LABEL_FAMILIES else "normal",
        "mapped_family": fam,
        "is_laundering": int(is_l),
        "laundering_type": str(ltype),
    }


def _iter_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert_csv_headers(reader.fieldnames or [])
        for row in reader:
            yield row


def _rss_mb() -> float:
    try:
        with open("/proc/self/status", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        return -1.0
    return -1.0


def _last_nonempty_line(path: Path) -> str:
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size <= 0:
            raise ValueError("empty SAML-D CSV")
        f.seek(max(0, size - 65536))
        chunk = f.read().decode("utf-8", errors="replace")
    lines = [ln for ln in chunk.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("empty SAML-D CSV")
    return lines[-1]


def calendar_from_ends(path: Path) -> tuple[datetime, datetime]:
    """t0/t1 from first and last CSV rows. Does not load the file."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert_csv_headers(reader.fieldnames or [])
        first = next(reader, None)
        if first is None:
            raise ValueError("empty SAML-D CSV")
        t0 = parse_event_ts(first["Date"], first["Time"])
    last = next(
        csv.DictReader(io.StringIO(_last_nonempty_line(path)), fieldnames=CSV_HEADERS)
    )
    t1 = parse_event_ts(last["Date"], last["Time"])
    if t1 < t0:
        raise ValueError("SAML-D last row is before first row; file may be unsorted")
    return t0, t1


def scan_calendar(path: Path) -> tuple[datetime, datetime, int, bool]:
    """One-row-at-a-time min/max. Does not load the CSV."""
    t0 = t1 = None
    n = 0
    prev = None
    sorted_ok = True
    for row in _iter_csv_rows(path):
        ts = parse_event_ts(row["Date"], row["Time"])
        n += 1
        if t0 is None:
            t0 = ts
        t1 = ts
        if prev is not None and ts < prev:
            sorted_ok = False
        prev = ts
        if n % 2_000_000 == 0:
            print(f"[saml-d] calendar scan {n}", flush=True)
    if t0 is None or t1 is None:
        raise ValueError("empty SAML-D CSV")
    return t0, t1, n, sorted_ok


def iter_replayed_rows(path: Path):
    """Causal FeatureComputer stream. Yields one feature row; never materializes the ledger."""
    fc = FeatureComputer()
    flags = empty_app_flags()
    n = 0
    for row in _iter_csv_rows(path):
        ts = parse_event_ts(row["Date"], row["Time"])
        payer = f"SAML-{row['Sender_account']}"
        payee = f"SAML-{row['Receiver_account']}"
        amount_minor = _amount_minor(row["Amount"])
        for pid in (payer, payee):
            if pid not in fc.accounts:
                fc.ensure(pid, ts, f"dev-{pid[-8:]}", KYC_DEFAULT, 10**15)
        snap = fc.snapshot_and_apply(
            ts=ts,
            payer=payer,
            payee=payee,
            amount_minor=amount_minor,
            device_hash=fc.accounts[payer].device_hash,
            app_flags=flags,
            debit=False,
        )
        snap.pop("_insufficient_float", None)
        fam = map_label_family(row["Is_laundering"], row["Laundering_type"])
        if fam in FORBIDDEN_FAMILIES:
            raise AssertionError("forbidden family leaked into SAML-D replay")
        out = _feature_row(snap, fam, row["Is_laundering"], row["Laundering_type"])
        out["event_ts"] = ts
        out["payee"] = payee
        n += 1
        if n % 500_000 == 0:
            print(
                f"[saml-d] replay {n} accounts={len(fc.accounts)} rss_mb={_rss_mb():.0f}",
                flush=True,
            )
            gc.collect()
        yield out


def replay_saml_d(csv_path: Path) -> pd.DataFrame:
    """Causal FeatureComputer pass for small fixtures. Do not call on the 9.5M CSV."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"SAML-D CSV not on disk: {path}. Place the Kaggle file at data/external/SAML-D.csv "
            "(gitignored). Adapter will not invent AP."
        )
    df = pd.DataFrame(list(iter_replayed_rows(path)))
    extra = set(df.columns) - set(TRAIN_ALLOWLIST) - {
        "mapped_family",
        "is_laundering",
        "laundering_type",
        "event_ts",
        "payee",
    }
    if extra:
        raise AssertionError(f"SAML-D replay leaked columns: {extra}")
    if bool(df["call_active_flag"].any()) or bool(df["beneficiary_changed"].any()):
        raise AssertionError("SAML-D replay must keep APP/invoice stamps false")
    if (df["mapped_family"].isin(FORBIDDEN_FAMILIES)).any():
        raise AssertionError("SAML-D mapped_family contains app_fraud or ato")
    return df


def eval_mask(ts: pd.Series, *, last_frac: float = 1.0 / 3.0) -> pd.Series:
    parsed = pd.to_datetime(ts, utc=True)
    t0, t1 = parsed.min(), parsed.max()
    cut = t0 + (t1 - t0) * (1.0 - last_frac)
    return parsed >= cut


def resolve_csv_path(csv_path: Path | None = None) -> Path | None:
    if csv_path is not None:
        pth = Path(csv_path)
        return pth if pth.is_file() else None
    for cand in CSV_CANDIDATES:
        if cand.is_file():
            return cand
    return None


SCORE_BATCH = 2048
_META_COLS = (
    "mapped_family",
    "is_laundering",
    "laundering_type",
    "event_ts",
    "payee",
    "payer",
    "event_id",
    "amount_minor",
)


def _score_batch(batch: list[dict[str, Any]], champ, rules) -> tuple[np.ndarray, np.ndarray, list[str]]:
    ev = pd.DataFrame(batch)
    y_bin = pd.to_numeric(ev["is_laundering"], errors="coerce").fillna(0).to_numpy(dtype=np.int8)
    fams = ev["mapped_family"].astype(str).tolist()
    scored = _attach_rule_bits(ev.drop(columns=list(_META_COLS), errors="ignore"), rules)
    x_raw = scored.reindex(columns=champ.raw_columns, fill_value=0)
    x, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=list(champ.cat_cols or CAT_COLS), fit=False)
    pmap = _proba_map(champ.model, x)
    if getattr(champ, "pmap_calibrators", None):
        pmap = _apply_pmap_calibrators(pmap, champ.pmap_calibrators, champ.classes)
    scores = _fraud_score(pmap, len(ev)).astype(np.float32, copy=False)
    return scores, y_bin, fams


def score_saml_d(
    csv_path: Path | None = None,
    *,
    model_run_id: str = "v1-train-46",
    models_dir: Path | None = None,
    negative_subsample_ratio: float | None = None,
) -> dict[str, Any]:
    """Stream FeatureComputer replay; score last-1/3 calendar in small batches. Never loads the full CSV."""
    path = resolve_csv_path(csv_path)
    if path is None:
        return {
            "status": "blocked_no_csv",
            "csv_path": str(csv_path or DEFAULT_CSV),
            "note": "FeatureComputer adapter is in-repo; Kaggle SAML-D.csv is not on disk.",
        }
    if negative_subsample_ratio is not None:
        raise ValueError(
            "negative subsample forbidden for headline SAML-D AP vs lab AP; "
            "lead TPR@FPR on full eval negatives"
        )
    t0, t1 = calendar_from_ends(path)
    cut = t0 + (t1 - t0) * (2.0 / 3.0)
    print(f"[saml-d] calendar-from-ends t0={t0} t1={t1} eval_cut={cut} rss_mb={_rss_mb():.0f}", flush=True)
    champ = load_champion(model_run_id, models_dir=models_dir)
    rules = load_v0_rules()
    thr = float(champ.detect_thr if champ.detect_thr is not None else champ.op_threshold)
    batch: list[dict[str, Any]] = []
    score_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    fam_parts: list[str] = []
    types_seen: set[str] = set()
    n_rows = 0
    n_scored_batches = 0
    prev_ts: datetime | None = None
    print("[saml-d] single-pass stream replay + batched eval score", flush=True)
    for row in iter_replayed_rows(path):
        n_rows += 1
        ts = row["event_ts"]
        if prev_ts is not None and ts < prev_ts:
            raise ValueError("SAML-D.csv is not time-sorted; refuse in-memory sort. Sort on disk first.")
        prev_ts = ts
        types_seen.add(str(row["laundering_type"]))
        if ts < cut:
            continue
        batch.append(row)
        if len(batch) >= SCORE_BATCH:
            sc, yb, fams = _score_batch(batch, champ, rules)
            score_parts.append(sc)
            y_parts.append(yb)
            fam_parts.extend(fams)
            batch = []
            n_scored_batches += 1
            if n_scored_batches % 32 == 0:
                gc.collect()
                print(
                    f"[saml-d] scored_batches={n_scored_batches} n_eval={sum(len(p) for p in y_parts)} rss_mb={_rss_mb():.0f}",
                    flush=True,
                )
    if batch:
        sc, yb, fams = _score_batch(batch, champ, rules)
        score_parts.append(sc)
        y_parts.append(yb)
        fam_parts.extend(fams)
    if not score_parts:
        raise ValueError("SAML-D eval slice empty")
    scores = np.concatenate(score_parts)
    y_bin = np.concatenate(y_parts)
    fam = np.asarray(fam_parts, dtype=object)
    yhat = (scores >= thr).astype(int)
    n_pos = {name: int((fam == name).sum()) for name in ("mule", "invoice_fraud", "unmapped", "normal")}
    fam_ap: dict[str, float | None] = {}
    for name in ("mule", "invoice_fraud"):
        yf = (fam == name).astype(int)
        fam_ap[name] = None if int(yf.sum()) < 30 else float(average_precision_score(yf, scores))
    mapped_counts = {name: int((fam == name).sum()) for name in sorted(set(fam_parts))}
    body = {
        "status": "scored",
        "dataset": "SAML-D",
        "csv_path": str(path),
        "n_rows": int(n_rows),
        "n_eval": int(len(y_bin)),
        "prevalence_eval": float(y_bin.mean()) if len(y_bin) else 0.0,
        "prevalence_stated": 0.001039,
        "model_run_id": model_run_id,
        "op_threshold": thr,
        "binary_ap": float(average_precision_score(y_bin, scores)) if y_bin.sum() else None,
        "precision_at_op": float(precision_score(y_bin, yhat, zero_division=0)),
        "recall_at_op": float(recall_score(y_bin, yhat, zero_division=0)),
        "tpr_at_fpr": {f"{t:g}": _tpr_at_fpr(y_bin, scores, t) for t in (0.001, 0.005, 0.01)},
        "n_pos": n_pos,
        "ap_by_mapped_family": fam_ap,
        "laundering_types": sorted(types_seen),
        "mapped_family_counts": mapped_counts,
        "negative_subsample_ratio": None,
        "featurecomputer_updates": int(n_rows),
        "streamed": True,
        "score_batch": SCORE_BATCH,
        "calendar_from_ends": True,
        "rail_analogue": RAIL_ANALOGUE,
        "note": (
            "Lead TPR@FPR. Streamed FeatureComputer; eval last 1/3 calendar scored in batches. "
            "Do not compare binary_ap to generate-dataset G-test AP. "
            "Authors: synthetic table will not fully capture real-world unpredictability."
        ),
    }
    return body


def write_stage4_artifacts(
    body: dict[str, Any],
    *,
    dest_dir: Path | None = None,
) -> Path:
    dest = dest_dir or Path("data/validation/v1")
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "stage4_saml_d.json"
    dest.joinpath("holdout_metrics.json" if body.get("status") == "scored" else "stage4_status.json").write_text(
        json.dumps(body, indent=2, default=str),
        encoding="utf-8",
    )
    out.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return out
