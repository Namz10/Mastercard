"""v0 rule file loader (defense_architecture §3.2)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from packages.catalog.features import normalize_feature_names

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "data" / "rules" / "v0_rules.yaml"


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    applies_to: str
    when: dict[str, Any]
    min_score: float | None = None
    reason: str = ""
    technique_ids: tuple[str, ...] = ()
    status: str = "live"


def load_v0_rules(path: Path | str | None = None) -> list[Rule]:
    rules_path = Path(path) if path else DEFAULT_RULES_PATH
    if not rules_path.is_file():
        return []
    raw = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("rules YAML must be a list")
    rules: list[Rule] = []
    for row in raw:
        when = row.get("when") or {}
        rules.append(
            Rule(
                id=str(row["id"]),
                kind=str(row.get("kind", "nudge")),
                applies_to=str(row.get("applies_to", "")),
                when=when,
                min_score=row.get("min_score"),
                reason=str(row.get("reason", "")),
                technique_ids=tuple(row.get("technique_ids") or []),
                status=str(row.get("status", "live")),
            )
        )
    return rules


def _condition_matches(when: dict[str, Any], features: set[str]) -> bool:
    """Rule when-block keys must appear in features_expected (auth-plane observable)."""
    if not when:
        return False
    for key in when:
        if key not in features:
            return False
    return True


def match_rules_to_features(
    features_expected: list[str],
    rules: list[Rule] | None = None,
) -> list[Rule]:
    loaded = rules if rules is not None else load_v0_rules()
    feat_set = set(normalize_feature_names(features_expected))
    matched: list[Rule] = []
    for rule in loaded:
        if rule.status != "live":
            continue
        if _condition_matches(rule.when, feat_set):
            matched.append(rule)
    return matched
