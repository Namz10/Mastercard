"""Grounder rejection rules (Plan 01 §3)."""

import re
from typing import Any

from packages.agents.embeddings import embed_text

# Within-run clone threshold (catalog cosine is applied in the librarian).
DEDUP_THRESHOLD = 0.92

EXPLOIT_PATTERNS = [
    r"\bexploit\s+payload\b",
    r"\bjailbreak-as-a-service\b",
    r"\bcriminal\s+market\b",
    r"\bdark\s*web\b",
    r"\bstep\s+\d+\s*:\s*download\b",
    r"\bmalware\s+payload\b",
]

BUZZWORD_ONLY = ["genai", "ai", "artificial intelligence", "generative"]


def is_exploit_content(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(p, lowered) for p in EXPLOIT_PATTERNS)


def is_buzzword_only(spec: dict[str, Any]) -> bool:
    controls = spec.get("control_bypassed") or []
    economic = spec.get("economic_class")
    name = (spec.get("name") or "").lower()
    if controls and economic:
        return False
    if any(b in name for b in BUZZWORD_ONLY) and not controls:
        return True
    return False


def has_payment_rail(spec: dict[str, Any]) -> bool:
    rail = spec.get("rail")
    return bool(rail) and rail != "none"


def _spec_embedding_key(spec: dict[str, Any]) -> list[float]:
    text = f"{spec.get('name', '')}|{spec.get('rail', '')}|{spec.get('technique_id', '')}"
    return embed_text(text)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def is_within_batch_duplicate(spec: dict[str, Any], kept: list[dict[str, Any]]) -> bool:
    """Reject only near-identical clones within the same Identify run."""
    key = _spec_embedding_key(spec)
    for other in kept:
        if _cosine(key, _spec_embedding_key(other)) > DEDUP_THRESHOLD:
            return True
    return False


def grounder_reject_reason(spec: dict[str, Any], body_text: str = "") -> str | None:
    if not has_payment_rail(spec):
        return "no_payment_rail"
    if is_buzzword_only(spec):
        return "buzzword_only"
    if is_exploit_content(body_text) or is_exploit_content(spec.get("name", "")):
        return "exploit_or_unsafe_content"
    return None


def apply_technique_reroute(spec: dict[str, Any], body_text: str = "") -> dict[str, Any]:
    """Deterministic technique_id correction before duplicate checks."""
    out = dict(spec)
    old_tid = str(out.get("technique_id") or "")
    text = (
        (out.get("name") or "")
        + " "
        + (out.get("one_liner") or "")
        + " "
        + body_text
    ).lower()
    lifecycle = str(out.get("lifecycle_stage") or "")

    if lifecycle == "onboarding_kyc" and any(
        m in text for m in ("deepfake", "liveness", "vkyc", "kyc")
    ):
        out["technique_id"] = "T09"
        out["category"] = 2
        out["rail"] = "onboarding"
        out.setdefault("simulator", {"injector_id": "identity_trajectory", "param_schema": {}})
        out["simulator"] = {"injector_id": "identity_trajectory", "param_schema": {}}
    elif lifecycle == "account_access_ato" and any(
        m in text for m in ("voice", "call center", "call centre")
    ):
        out["technique_id"] = "T12"
        out["category"] = 2

    if old_tid != out.get("technique_id"):
        out["_reroute_from"] = old_tid
    return out


def filter_proposed_specs(
    specs: list[dict[str, Any]],
    body_by_url: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    kept: list[dict[str, Any]] = []
    errors: list[str] = []
    for spec in specs:
        url = (spec.get("source_urls") or ["unknown"])[0]
        body = body_by_url.get(str(url), "")
        spec = apply_technique_reroute(spec, body)
        if spec.get("_reroute_from"):
            errors.append(
                f"technique_reroute:{spec.get('vector_id')}:{spec['_reroute_from']}->{spec.get('technique_id')}"
            )
            spec = {k: v for k, v in spec.items() if k != "_reroute_from"}
        reason = grounder_reject_reason(spec, body)
        if reason:
            errors.append(f"grounder_reject:{spec.get('vector_id')}:{reason}")
            continue
        if is_within_batch_duplicate(spec, kept):
            errors.append(f"grounder_reject:{spec.get('vector_id')}:duplicate_in_batch")
            continue
        kept.append(spec)
    return kept, errors
