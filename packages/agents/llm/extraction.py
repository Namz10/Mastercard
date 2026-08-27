"""Identify extraction: OmniRoute JSON or deterministic rules; abstain when weak."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from packages.agents.llm.config import is_llm_configured, load_provider_config
from packages.agents.llm.errors import LlmError
from packages.agents.llm.providers import build_provider
from packages.agents.settings import get_identify_settings
from packages.catalog.features import enrich_spec_features
from packages.catalog.models import AttackSpec
from packages.catalog.schemas import INJECTOR_SIGNAL_MODELS, validate_simulatable_signals
from packages.osint.allowlist import tier_for_domain
from packages.osint.telemetry.indicators import propose_indicators_from_text

_VALID_INJECTORS = frozenset(INJECTOR_SIGNAL_MODELS.keys())

_INJECTOR_ALIASES: dict[str, str] = {
    "graph_mule": "graph_mule",
    "identity_trajectory": "identity_trajectory",
    "app_session": "app_session",
    "doc_beneficiary": "doc_beneficiary",
    "deepfake_kyc_injector": "identity_trajectory",
    "deepfake_kyc": "identity_trajectory",
    "kyc_injector": "identity_trajectory",
    "identity_injector": "identity_trajectory",
    "mule_graph": "graph_mule",
    "app_injector": "app_session",
}

_EXTRACTION_SCHEMA_HINT = """
Return a JSON object with ALL of these fields (use null only if truly unknown):
vector_id (slug string), technique_id (T01-T24), name, one_liner, category (1-5), rail,
lifecycle_stage, genai_modality, social_surface, control_bypassed (list), actor_type,
economic_class, is_authorized_push (bool), generate_mode (generate|name_only),
source_urls (list of https URLs), simulatable_signals (object), simulator (object with injector_id).
network_indicators (optional list): only when the article explicitly names attack infrastructure —
each item: type (ip|domain), value, role (scanner|botnet|c2|card_testing|stuffing_source|credential_stuffing),
evidence_span (verbatim quote from the article containing the indicator, max 200 chars).
Use [] or omit if no attack infrastructure is named. Never invent indicators. Exclude victim/bank/CDN IPs.
Do not include exploit steps, payloads, or criminal tooling instructions.
If the article is not a payment-fraud typology, return {"abstain": true, "reason": "..."}.
"""

_TECHNIQUE_DEFAULTS: dict[str, tuple[int, str]] = {
    "T01": (1, "graph_mule"),
    "T02": (1, "graph_mule"),
    "T03": (1, "graph_mule"),
    "T04": (1, "graph_mule"),
    "T05": (1, "graph_mule"),
    "T06": (1, "graph_mule"),
    "T07": (1, "graph_mule"),
    "T08": (2, "identity_trajectory"),
    "T09": (2, "identity_trajectory"),
    "T10": (2, "identity_trajectory"),
    "T11": (2, "identity_trajectory"),
    "T12": (2, "identity_trajectory"),
    "T13": (3, "app_session"),
    "T14": (3, "app_session"),
    "T15": (3, "app_session"),
    "T16": (3, "app_session"),
    "T17": (3, "app_session"),
    "T18": (3, "app_session"),
    "T19": (3, "app_session"),
    "T20": (4, "graph_mule"),
    "T21": (4, "graph_mule"),
    "T22": (4, "graph_mule"),
    "T23": (4, "graph_mule"),
    "T24": (5, "doc_beneficiary"),
}

_VALID_RAILS = frozenset(
    {"upi_like", "imps", "neft", "rtgs", "card_cnp", "card_cp", "wire", "crypto_offramp", "onboarding"}
)
_VALID_LIFECYCLE = frozenset(
    {
        "onboarding_kyc",
        "account_access_ato",
        "payment_initiation",
        "authorization",
        "clearing_settlement",
        "disbursement_mule",
        "dispute_sar",
    }
)
_VALID_MODALITY = frozenset({"text", "voice", "video", "document", "bot", "poisoning", "mixed"})
_VALID_SOCIAL = frozenset({"email", "sms", "voice", "video_call", "in_app", "merchant", "none"})
_VALID_ECONOMIC = frozenset({"APP", "ATO", "CNP", "mule", "BEC", "detector"})
_VALID_ACTOR = frozenset({"consumer", "merchant"})
_VALID_GENERATE_MODE = frozenset({"generate", "name_only"})
_VALID_CONFIDENCE = frozenset({"confirmed", "reported-unverified"})
_VALID_CORROBORATION = frozenset({"network-telemetry", "documentary-case", "not-yet-corroborated"})
_VALID_VECTOR_CLASS = frozenset({"network_footprint", "human_social"})
_VALID_DUAL_USE = frozenset({"low", "medium", "high"})

_RAIL_ALIASES: dict[str, str] = {
    "digital onboarding": "onboarding",
    "digital_onboarding": "onboarding",
    "onboarding": "onboarding",
    "kyc": "onboarding",
    "vkyc": "onboarding",
    "upi": "upi_like",
    "upi_like": "upi_like",
    "instant payment": "upi_like",
    "card": "card_cnp",
    "card_cnp": "card_cnp",
    "cnp": "card_cnp",
    "wire transfer": "wire",
    "wire": "wire",
    "crypto": "crypto_offramp",
    "crypto_offramp": "crypto_offramp",
}

_LIFECYCLE_ALIASES: dict[str, str] = {
    "onboarding": "onboarding_kyc",
    "onboarding_kyc": "onboarding_kyc",
    "kyc": "onboarding_kyc",
    "account access": "account_access_ato",
    "account_access": "account_access_ato",
    "ato": "account_access_ato",
    "payment": "payment_initiation",
    "payment_initiation": "payment_initiation",
    "authorization": "authorization",
    "clearing": "clearing_settlement",
    "settlement": "clearing_settlement",
    "mule": "disbursement_mule",
    "disbursement": "disbursement_mule",
    "dispute": "dispute_sar",
}

_ECONOMIC_ALIASES: dict[str, str] = {
    "app": "APP",
    "authorized push": "APP",
    "authorized_push": "APP",
    "ato": "ATO",
    "account takeover": "ATO",
    "cnp": "CNP",
    "mule": "mule",
    "bec": "BEC",
    "business email compromise": "BEC",
    "detector": "detector",
}

_NAME_ONLY_TECHNIQUES = frozenset({"T20", "T21", "T22", "T23"})


def _snake_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _coerce_enum(
    value: Any,
    allowed: frozenset[str],
    aliases: dict[str, str],
    case_sensitive: bool = False,
) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    candidates = [raw, raw.lower(), _snake_token(raw)]
    for cand in candidates:
        if case_sensitive and cand in allowed:
            return cand
        if not case_sensitive and cand.lower() in {a.lower() for a in allowed}:
            for a in allowed:
                if a.lower() == cand.lower():
                    return a
    for cand in [raw.lower(), _snake_token(raw)]:
        if cand in aliases:
            return aliases[cand]
    lower = raw.lower()
    for phrase, mapped in aliases.items():
        if phrase in lower and mapped in allowed:
            return mapped
    return None


def normalize_llm_raw(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    tid = out.get("technique_id")
    if tid is not None:
        tid_s = str(tid).strip().upper()
        if re.match(r"^T\d{2}$", tid_s):
            out["technique_id"] = tid_s

    coerced = _coerce_enum(out.get("rail"), _VALID_RAILS, _RAIL_ALIASES)
    if coerced:
        out["rail"] = coerced
    elif "rail" in out:
        del out["rail"]

    lc = _coerce_enum(out.get("lifecycle_stage"), _VALID_LIFECYCLE, _LIFECYCLE_ALIASES)
    if lc:
        out["lifecycle_stage"] = lc
    elif "lifecycle_stage" in out:
        del out["lifecycle_stage"]

    mod = _coerce_enum(out.get("genai_modality"), _VALID_MODALITY, {})
    if mod:
        out["genai_modality"] = mod
    elif "genai_modality" in out:
        del out["genai_modality"]

    soc = _coerce_enum(out.get("social_surface"), _VALID_SOCIAL, {})
    if soc:
        out["social_surface"] = soc
    elif "social_surface" in out:
        del out["social_surface"]

    econ = _coerce_enum(out.get("economic_class"), _VALID_ECONOMIC, _ECONOMIC_ALIASES, case_sensitive=True)
    if econ:
        out["economic_class"] = econ
    elif "economic_class" in out:
        del out["economic_class"]

    actor = _coerce_enum(out.get("actor_type"), _VALID_ACTOR, {})
    if actor:
        out["actor_type"] = actor
    elif "actor_type" in out:
        del out["actor_type"]

    gm = _coerce_enum(out.get("generate_mode"), _VALID_GENERATE_MODE, {})
    if gm:
        out["generate_mode"] = gm

    conf = out.get("confidence_level")
    if conf is not None:
        conf_s = str(conf).strip().lower().replace("_", "-")
        if conf_s in _VALID_CONFIDENCE:
            out["confidence_level"] = conf_s
        else:
            del out["confidence_level"]

    vc = _coerce_enum(out.get("vector_class"), _VALID_VECTOR_CLASS, {})
    if vc:
        out["vector_class"] = vc

    du = _coerce_enum(out.get("dual_use_rating"), _VALID_DUAL_USE, {})
    if du:
        out["dual_use_rating"] = du

    corr = out.get("corroboration_type")
    if corr is not None:
        corr_s = str(corr).strip().lower().replace("_", "-")
        if corr_s in _VALID_CORROBORATION:
            out["corroboration_type"] = corr_s
        else:
            del out["corroboration_type"]

    return out


def _slug_vector_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    return f"identify-{slug}"


def _coerce_network_indicators(raw_value: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        out.append(dict(item))
    return out


def _default_signals(injector: str) -> dict[str, Any]:
    if injector == "identity_trajectory":
        return {
            "seasoning_days": 0,
            "seasoning_txn_count": 0,
            "liveness_score": 0.35,
            "doc_consistency": 0.8,
            "device_hash_shift": False,
            "kyc_tier": "tier2",
        }
    if injector == "app_session":
        return {
            "persuasion_labels": ["bank_impersonation", "urgency"],
            "call_active_flag": True,
            "copy_paste_payee_flag": True,
            "pause_ms": 4000,
            "new_payee": True,
            "urgency_pressure": 0.85,
        }
    if injector == "graph_mule":
        return {
            "fan_in_1h": 15,
            "fan_out_ttl_hours": 2.0,
            "smurf_cap_ratio": 0.9,
            "hop_rails": ["upi_like"],
            "mule_account_age_days": 7,
            "cashout_mcc_or_sink": "crypto_offramp",
        }
    return {}


def _abstain(reason: str, source_url: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "extraction_source": "abstain",
        "abstain": True,
        "abstain_reason": reason,
        "source_urls": [source_url],
        "status": "proposed",
    }
    if extra:
        payload.update(extra)
    return payload


def rule_based_extract(article_text: str, source_url: str, source_domain: str) -> dict[str, Any] | None:
    """Deterministic extraction for known fixture patterns. Returns None to abstain."""
    text = article_text.lower()
    tier = tier_for_domain(source_domain)

    if "deepfake" in text and ("kyc" in text or "liveness" in text or "vkyc" in text):
        technique_id = "T09"
        category = 2
        rail = "onboarding"
        lifecycle = "onboarding_kyc"
        modality = "video"
        economic = "ATO"
        injector = "identity_trajectory"
        name = "Deepfake VKYC liveness bypass (identified)"
        network_indicators: list[dict[str, Any]] = []
    elif "card testing" in text or "card-testing" in text or "credential stuffing" in text:
        technique_id = "T07"
        category = 1
        rail = "card_cnp"
        lifecycle = "authorization"
        modality = "bot"
        economic = "CNP"
        injector = "graph_mule"
        name = "Card-testing botnet on payment APIs (identified)"
        network_indicators = propose_indicators_from_text(article_text)
    elif "upi" in text or "impersonation" in text or "authorized push" in text:
        technique_id = "T13"
        category = 3
        rail = "upi_like"
        lifecycle = "payment_initiation"
        modality = "voice"
        economic = "APP"
        injector = "app_session"
        name = "UPI impersonation APP (identified)"
        network_indicators = []
    elif "mule" in text or "fan-in" in text or "cash-out" in text:
        technique_id = "T01"
        category = 1
        rail = "upi_like"
        lifecycle = "disbursement_mule"
        modality = "bot"
        economic = "mule"
        injector = "graph_mule"
        name = "Mule fan-in funnel (identified)"
        network_indicators = []
    else:
        return None

    signals = _default_signals(injector)
    controls: list[str] = []
    if "liveness" in text:
        controls.append("liveness")
    if "kyc" in text:
        controls.append("static_kyc")
    if "velocity" in text:
        controls.append("velocity_rule")
    if "otp" in text:
        controls.append("otp")
    if "callback" in text or "human" in text:
        controls.append("human_callback")
    if not controls:
        controls = ["human_callback"]

    spec: dict[str, Any] = {
        "vector_id": _slug_vector_id(name),
        "technique_id": technique_id,
        "name": name,
        "one_liner": name,
        "category": category,
        "rail": rail,
        "lifecycle_stage": lifecycle,
        "genai_modality": modality,
        "social_surface": "voice" if modality == "voice" else "in_app",
        "control_bypassed": controls,
        "actor_type": "consumer",
        "economic_class": economic,
        "is_authorized_push": economic in {"APP", "BEC"},
        "generate_mode": "name_only" if technique_id in _NAME_ONLY_TECHNIQUES else "generate",
        "dual_use_rating": "low",
        "source_tier": tier,
        "confidence_level": "confirmed" if tier <= 2 else "reported-unverified",
        "corroboration_type": "not-yet-corroborated",
        "vector_class": "human_social",
        "source_urls": [source_url],
        "simulatable_signals": signals,
        "simulator": {"injector_id": injector, "param_schema": {}},
        "features_expected": [],
        "entities": ["victim", "mule"],
        "status": "proposed",
        "extraction_source": "rules",
        "network_indicators": network_indicators,
    }
    return enrich_spec_features(spec)


def _complete_from_llm(raw: dict[str, Any], source_url: str, source_domain: str) -> dict[str, Any] | None:
    """Validate LLM JSON; fill technique-keyed defaults only. No rule-skeleton overlay."""
    if raw.get("abstain") is True:
        return None
    raw = normalize_llm_raw(raw)
    tid = str(raw.get("technique_id") or "").upper()
    if tid not in _TECHNIQUE_DEFAULTS:
        return None
    cat, injector = _TECHNIQUE_DEFAULTS[tid]
    name = str(raw.get("name") or "").strip()
    if not name:
        return None

    generate_mode = raw.get("generate_mode") or (
        "name_only" if tid in _NAME_ONLY_TECHNIQUES else "generate"
    )
    if generate_mode == "generate" and tid in _NAME_ONLY_TECHNIQUES:
        generate_mode = "name_only"

    sim = raw.get("simulator") if isinstance(raw.get("simulator"), dict) else {}
    injector_id = sim.get("injector_id") or injector
    resolved = _coerce_enum(injector_id, _VALID_INJECTORS, _INJECTOR_ALIASES) or injector

    signals = raw.get("simulatable_signals") if isinstance(raw.get("simulatable_signals"), dict) else {}
    if generate_mode == "generate" and not signals:
        signals = _default_signals(resolved)

    spec: dict[str, Any] = {
        "vector_id": raw.get("vector_id") or _slug_vector_id(name),
        "technique_id": tid,
        "name": name,
        "one_liner": raw.get("one_liner") or name,
        "category": raw.get("category") or cat,
        "rail": raw.get("rail") or ("onboarding" if tid.startswith("T0") and tid <= "T12" and tid >= "T08" else "upi_like"),
        "lifecycle_stage": raw.get("lifecycle_stage") or "payment_initiation",
        "genai_modality": raw.get("genai_modality") or "text",
        "social_surface": raw.get("social_surface") or "in_app",
        "control_bypassed": raw.get("control_bypassed") or ["human_callback"],
        "actor_type": raw.get("actor_type") or "consumer",
        "economic_class": raw.get("economic_class") or "APP",
        "is_authorized_push": raw.get("is_authorized_push")
        if isinstance(raw.get("is_authorized_push"), bool)
        else False,
        "generate_mode": generate_mode,
        "dual_use_rating": raw.get("dual_use_rating") or "low",
        "source_tier": tier_for_domain(source_domain),
        "confidence_level": raw.get("confidence_level") or "reported-unverified",
        "corroboration_type": raw.get("corroboration_type") or "not-yet-corroborated",
        "vector_class": raw.get("vector_class") or "human_social",
        "source_urls": [source_url],
        "simulatable_signals": signals if generate_mode == "generate" else {},
        "simulator": {"injector_id": resolved, "param_schema": sim.get("param_schema") or {}},
        "features_expected": raw.get("features_expected") or [],
        "entities": raw.get("entities") or ["victim"],
        "status": "proposed",
        "extraction_source": "llm",
        "network_indicators": _coerce_network_indicators(raw.get("network_indicators")),
    }
    if spec["generate_mode"] == "generate":
        try:
            spec["simulatable_signals"] = validate_simulatable_signals(resolved, spec["simulatable_signals"])
        except Exception:
            spec["generate_mode"] = "name_only"
            spec["simulatable_signals"] = {}

    try:
        AttackSpec.model_validate(spec)
    except ValidationError:
        return None
    return enrich_spec_features(spec)


def _is_survey_not_typology(article_text: str, source_url: str) -> bool:
    head = article_text[:2500].lower()
    url_lower = source_url.lower()
    if "arxiv.org" not in url_lower:
        return False
    survey_markers = (
        "global survey",
        "we survey",
        "literature review",
        "systematic survey",
        "a survey of",
    )
    return any(m in head for m in survey_markers)


def extract_attack_json(article_text: str, source_url: str) -> dict[str, Any]:
    cfg = load_provider_config()
    provider = build_provider(cfg)
    settings = get_identify_settings()
    article_cap = settings.identify_llm_article_chars
    brief = ""
    try:
        from packages.catalog.taxonomy_brief import build_taxonomy_brief

        brief = build_taxonomy_brief()
    except Exception:
        brief = ""
    taxonomy_block = f"\nTaxonomy reference (map to existing T01-T24 when possible):\n{brief}\n" if brief else ""
    prompt = (
        f"Extract one GenAI payment fraud attack vector from this allowlisted source.\n"
        f"Abstain for survey papers, generic vendor fluff, or non-payment typologies.\n"
        f"Map to existing technique_id when the article matches a known typology.\n"
        f"Source URL: {source_url}\n"
        f"{taxonomy_block}\nArticle:\n{article_text[:article_cap]}\n\n{_EXTRACTION_SCHEMA_HINT}"
    )
    return provider.complete_json(
        system=(
            "You extract payment fraud typology for a bank defense lab. "
            "Respond with a single JSON object only, no markdown."
        ),
        user=prompt,
        schema_name="AttackExtract",
    )


def extract_from_document(
    article_text: str,
    source_url: str,
    source_domain: str,
    max_retries: int = 2,
) -> dict[str, Any]:
    if _is_survey_not_typology(article_text, source_url):
        return _abstain("survey_not_typology", source_url)

    last_error: str | None = None
    if is_llm_configured():
        for _ in range(max_retries):
            try:
                raw = extract_attack_json(article_text, source_url)
                completed = _complete_from_llm(raw, source_url, source_domain)
                if completed is None:
                    return _abstain("llm_invalid_or_weak", source_url)
                return completed
            except LlmError as exc:
                last_error = redact_error(str(exc))
                continue
            except Exception as exc:
                last_error = redact_error(str(exc)[:240])
                continue

    rules = rule_based_extract(article_text, source_url, source_domain)
    if rules is None:
        extra = {"llm_last_error": last_error} if last_error else None
        return _abstain("weak_or_unknown_article", source_url, extra)
    if last_error:
        rules["llm_last_error"] = last_error
    return rules


def redact_error(message: str) -> str:
    from packages.agents.llm.transport import redact_secrets

    return redact_secrets(message)[:240]


# Back-compat aliases used nowhere after migration; keep names for grep-friendly docs.
normalize_groq_raw = normalize_llm_raw
