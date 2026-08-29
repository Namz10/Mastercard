"""Brake — mitigation enum from predicted family + rule hits (Plan 12 Lock 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from packages.policy.rules import Rule, RuleEval

PolicyAction = Literal[
    "allow",
    "notify",
    "step_up",
    "hold",
    "decline",
    "mule_credit_restrict",
    "case",
]

POLICY_ACTIONS: tuple[str, ...] = (
    "allow",
    "notify",
    "step_up",
    "hold",
    "decline",
    "mule_credit_restrict",
    "case",
)

ATO_DECLINE_SCORE = 0.5
APP_HOLD_SCORE = 0.65
DEFAULT_ACT_THR = 0.5
HUB_PAYEE_PREFIX = "VID-SIM-HUB-"


def _is_hub_payee(payee: str | None) -> bool:
    return str(payee or "").startswith(HUB_PAYEE_PREFIX)


def _filter_hits_for_payee(rules: list[Rule], payee: str | None) -> list[Rule]:
    if not _is_hub_payee(payee):
        return rules
    return [r for r in rules if r.id != "mule-fan-in-burst"]


@dataclass(frozen=True)
class BrakeDecision:
    policy_action: PolicyAction
    reason_codes: tuple[str, ...]
    score: float
    pred_label_family: str


def _hits_of(eval_or_hits: RuleEval | list[Rule] | tuple[Rule, ...]) -> list[Rule]:
    if isinstance(eval_or_hits, RuleEval):
        return list(eval_or_hits.hits)
    return list(eval_or_hits)


def brake(
    *,
    pred_label_family: str,
    score: float,
    hits: RuleEval | list[Rule] | tuple[Rule, ...] | None = None,
    payee: str | None = None,
    act_thr: float | None = None,
) -> BrakeDecision:
    """
    Live order already ran rules. This table maps family + hits + score → action.
    APP never silent-declines. ATO may decline. Mule payee → credit restrict.
    Calm-down + no hard_flag → allow (genuine kirana/rent), even if the model is noisy.
    Hub payees (VID-SIM-HUB-*) skip mule-fan-in-burst — high fan-in is expected merchant behavior.
    """
    rules = _filter_hits_for_payee(_hits_of(hits or []), payee)
    rules = [
        r
        for r in rules
        if r.min_score is None or score >= float(r.min_score)
    ]
    kinds = {r.kind for r in rules}
    applies = {r.applies_to.lower() for r in rules if r.kind == "hard_flag"}
    reasons = [r.id for r in rules]
    family = (pred_label_family or "normal").lower()
    hard = "hard_flag" in kinds
    calm = "calm_down" in kinds
    act = float(act_thr) if act_thr is not None else DEFAULT_ACT_THR
    mule_hit = family == "mule" and score >= act
    mule_hit = mule_hit or "mule" in applies
    app_hit = family == "app_fraud" or "app" in applies
    ato_hit = family == "ato" or "ato" in applies
    invoice_hit = family == "invoice_fraud" or "bec" in applies

    action: PolicyAction
    if mule_hit:
        action = "mule_credit_restrict"
        reasons = ["pred:mule" if family == "mule" else "rule:mule", *reasons]
    elif calm and not hard:
        action = "allow"
        reasons = ["calm_down", *reasons]
    elif app_hit:
        action = "hold" if (hard or score >= APP_HOLD_SCORE) else "notify"
        reasons = ["pred:app_fraud" if family == "app_fraud" else "rule:APP", *reasons]
    elif invoice_hit:
        action = "hold" if (hard or score >= ATO_DECLINE_SCORE) else "case"
        reasons = ["pred:invoice_fraud" if family == "invoice_fraud" else "rule:BEC", *reasons]
    elif ato_hit:
        action = "decline" if (hard or score >= ATO_DECLINE_SCORE) else "step_up"
        reasons = ["pred:ato" if family == "ato" else "rule:ATO", *reasons]
    elif family == "identity_burst":
        action = "step_up" if score >= ATO_DECLINE_SCORE else "notify"
        reasons = ["pred:identity_burst", *reasons]
    elif score >= APP_HOLD_SCORE:
        action = "notify"
        reasons = ["score_elevated", *reasons]
    else:
        action = "allow"
        if not reasons:
            reasons = ["low_score"]

    if action == "decline" and app_hit and not mule_hit:
        action = "hold"
        reasons = ["app_no_decline", *reasons]

    return BrakeDecision(
        policy_action=action,
        reason_codes=tuple(dict.fromkeys(reasons)),
        score=float(score),
        pred_label_family=pred_label_family,
    )


def as_record(decision: BrakeDecision) -> dict[str, Any]:
    return {
        "policy_action": decision.policy_action,
        "reason_codes": list(decision.reason_codes),
        "score": decision.score,
        "pred_label_family": decision.pred_label_family,
    }
