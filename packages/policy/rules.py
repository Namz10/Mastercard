"""v0 rules — row-value predicates, not key-presence (Plan 12 Phase B)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from packages.catalog.features import normalize_feature_names
from packages.sim.export import TRAIN_ALLOWLIST, TRAIN_DENYLIST

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "data" / "rules" / "v0_rules.yaml"

FORBIDDEN_RULE_FIELDS = frozenset(
    {
        "smurf_cap_ratio",
        "seasoning_days",
        "seasoning_txn_count",
        "fan_out_ttl_hours",
        "mule_account_age_days",
        "gstin",
        "is_authorized_push",
        "vector_id",
        "injector_id",
        "technique_id",
        "simulatable_signals",
        "economic_class",
        "label_class",
        "world_seed",
        "transcripts",
        "payload",
        "persona_type",
    }
)

# Not in train.parquet X, but observable on a flattened auth row (invoice payload booleans).
EXTRA_ROW_FIELDS = frozenset({"beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag"})

ALLOWED_RULE_FIELDS = (set(TRAIN_ALLOWLIST) - {"label_family"}) | EXTRA_ROW_FIELDS

# Loop C: catalog still names knobs; live rules use allowlist columns.
COVERAGE_EQUIV: dict[str, frozenset[str]] = {
    "account_age_days": frozenset({"account_age_days", "mule_account_age_days", "seasoning_days"}),
    "fan_in_1h": frozenset({"fan_in_1h"}),
    "fan_in_unique_payers_1h": frozenset({"fan_in_unique_payers_1h"}),
    "fan_out_1h": frozenset({"fan_out_1h", "fan_out_ttl_hours", "hop_rails"}),
    "burst_velocity": frozenset(
        {"burst_velocity", "seasoning_txn_count", "velocity_jump", "windowed_fan_in"}
    ),
    "amount_vs_p30": frozenset({"amount_vs_p30", "smurf_cap_ratio"}),
    "is_new_device": frozenset({"is_new_device", "device_hash_shift"}),
    "is_new_payee": frozenset({"is_new_payee", "new_payee"}),
    "call_active_flag": frozenset({"call_active_flag"}),
    "copy_paste_payee_flag": frozenset({"copy_paste_payee_flag"}),
    "pause_ms": frozenset({"pause_ms"}),
    "urgency_pressure": frozenset({"urgency_pressure"}),
    "beneficiary_changed": frozenset({"beneficiary_changed"}),
    "gstin_checksum_ok": frozenset({"gstin_checksum_ok"}),
    "lookalike_domain_flag": frozenset({"lookalike_domain_flag"}),
}

_PRED_RE = re.compile(
    r"^(?P<field>[a-z_][a-z0-9_]*)\s*(?P<op>==|!=|>=|<=|>|<)\s*(?P<raw>.+)$",
    re.IGNORECASE,
)

KIND_ORDER = ("hard_flag", "nudge", "calm_down")


@dataclass(frozen=True)
class Predicate:
    field: str
    op: str
    value: Any


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    applies_to: str
    when: tuple[str, ...]
    predicates: tuple[Predicate, ...]
    min_score: float | None = None
    reason: str = ""
    technique_ids: tuple[str, ...] = ()
    status: str = "live"


@dataclass(frozen=True)
class RuleEval:
    hits: tuple[Rule, ...]
    kinds: tuple[str, ...]

    @property
    def hard_flags(self) -> tuple[Rule, ...]:
        return tuple(r for r in self.hits if r.kind == "hard_flag")

    @property
    def calm_downs(self) -> tuple[Rule, ...]:
        return tuple(r for r in self.hits if r.kind == "calm_down")


def _parse_value(raw: str) -> Any:
    text = raw.strip()
    low = text.lower()
    if low in {"true", "yes"}:
        return True
    if low in {"false", "no"}:
        return False
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse_predicate(expr: str) -> Predicate:
    m = _PRED_RE.match(expr.strip())
    if not m:
        raise ValueError(f"invalid rule predicate: {expr!r}")
    field = m.group("field")
    if field in FORBIDDEN_RULE_FIELDS or field in TRAIN_DENYLIST:
        raise ValueError(f"forbidden rule field: {field}")
    if field not in ALLOWED_RULE_FIELDS:
        raise ValueError(f"rule field not on allowlist: {field}")
    return Predicate(field=field, op=m.group("op"), value=_parse_value(m.group("raw")))


def _when_to_exprs(when: Any) -> list[str]:
    if when is None:
        return []
    if isinstance(when, list):
        return [str(x) for x in when]
    if isinstance(when, dict):
        exprs: list[str] = []
        for key, val in when.items():
            if isinstance(val, bool):
                exprs.append(f"{key} == {str(val).lower()}")
            else:
                exprs.append(f"{key} == {val}")
        return exprs
    raise ValueError("rule `when` must be a list of predicates")


def parse_when(when: Any) -> tuple[tuple[str, ...], tuple[Predicate, ...]]:
    exprs = tuple(_when_to_exprs(when))
    preds = tuple(parse_predicate(e) for e in exprs)
    return exprs, preds


def load_v0_rules(path: Path | str | None = None) -> list[Rule]:
    rules_path = Path(path) if path else DEFAULT_RULES_PATH
    if not rules_path.is_file():
        return []
    raw = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("rules YAML must be a list")
    rules: list[Rule] = []
    kinds_seen: set[str] = set()
    for row in raw:
        exprs, preds = parse_when(row.get("when"))
        kind = str(row.get("kind", "nudge"))
        kinds_seen.add(kind)
        rules.append(
            Rule(
                id=str(row["id"]),
                kind=kind,
                applies_to=str(row.get("applies_to", "")),
                when=exprs,
                predicates=preds,
                min_score=row.get("min_score"),
                reason=str(row.get("reason", "")),
                technique_ids=tuple(row.get("technique_ids") or []),
                status=str(row.get("status", "live")),
            )
        )
    missing = [k for k in KIND_ORDER if k not in kinds_seen]
    if missing:
        raise ValueError(f"v0 rules must include kinds {KIND_ORDER}; missing {missing}")
    return rules


def _coerce(row_val: Any, expected: Any) -> Any:
    if isinstance(expected, bool):
        if isinstance(row_val, str):
            return row_val.strip().lower() in {"1", "true", "yes"}
        return bool(row_val)
    if isinstance(expected, int) and not isinstance(expected, bool):
        return int(row_val)
    if isinstance(expected, float):
        return float(row_val)
    return row_val


def _compare(row_val: Any, op: str, expected: Any) -> bool:
    left = _coerce(row_val, expected)
    if op == "==":
        return left == expected
    if op == "!=":
        return left != expected
    if op == ">=":
        return left >= expected
    if op == "<=":
        return left <= expected
    if op == ">":
        return left > expected
    if op == "<":
        return left < expected
    return False


def flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    """Ledger event or already-flat train/auth dict → predicate namespace."""
    if "features_auth" in row or "party_ids" in row:
        fa = dict(row.get("features_auth") or {})
        payload = row.get("payload") or {}
        parties = row.get("party_ids") or {}
        out: dict[str, Any] = {**fa}
        out["rail"] = row.get("rail")
        out["kyc_tier"] = row.get("kyc_tier") or fa.get("kyc_tier")
        out["label_family"] = row.get("label_family")
        out["payer"] = parties.get("payer")
        out["payee"] = parties.get("payee")
        out["amount_minor"] = row.get("amount_minor")
        for key in EXTRA_ROW_FIELDS:
            if key in payload:
                out[key] = payload[key]
            elif key in fa:
                out[key] = fa[key]
        return out
    return dict(row)


def predicate_holds(pred: Predicate, row: dict[str, Any]) -> bool:
    if pred.field not in row or row[pred.field] is None:
        return False
    try:
        return _compare(row[pred.field], pred.op, pred.value)
    except (TypeError, ValueError):
        return False


def rule_fires(rule: Rule, row: dict[str, Any]) -> bool:
    if not rule.predicates:
        return False
    flat = flatten_row(row)
    return all(predicate_holds(p, flat) for p in rule.predicates)


def evaluate_rules(
    row: dict[str, Any],
    rules: list[Rule] | None = None,
) -> RuleEval:
    loaded = rules if rules is not None else load_v0_rules()
    hits = tuple(r for r in loaded if r.status == "live" and rule_fires(r, row))
    kinds = tuple(dict.fromkeys(r.kind for r in hits))
    return RuleEval(hits=hits, kinds=kinds)


def _field_covered(field: str, features: set[str]) -> bool:
    aliases = COVERAGE_EQUIV.get(field, frozenset({field}))
    return bool(aliases & features)


def _condition_matches(rule: Rule, features: set[str]) -> bool:
    if not rule.predicates:
        return False
    return all(_field_covered(p.field, features) for p in rule.predicates)


def match_rules_to_features(
    features_expected: list[str],
    rules: list[Rule] | None = None,
) -> list[Rule]:
    """Coverage map only: catalog feature names vs rule fields (with knob aliases)."""
    loaded = rules if rules is not None else load_v0_rules()
    feat_set = set(normalize_feature_names(features_expected))
    matched: list[Rule] = []
    for rule in loaded:
        if rule.status != "live":
            continue
        if rule.kind == "calm_down":
            continue
        if _condition_matches(rule, feat_set):
            matched.append(rule)
    return matched


def promote_from_draft(draft_id: str, **kwargs) -> dict:
    from packages.policy.rule_hitl import approve_draft
    return approve_draft(draft_id, **kwargs)
