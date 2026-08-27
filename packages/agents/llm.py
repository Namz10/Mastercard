"""LLM structured extraction (Groq OpenAI-compatible API)."""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

from packages.agents.settings import DEFAULT_GROQ_API_BASE, DEFAULT_GROQ_MODEL, GROQ_MODEL_FALLBACKS
from packages.catalog.schemas import INJECTOR_SIGNAL_MODELS, validate_simulatable_signals

DEFAULT_MODEL = DEFAULT_GROQ_MODEL

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
Do not include exploit steps, payloads, or criminal tooling instructions.
"""

# technique_id → (category, default injector_id for generate_mode=generate)
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

_OVERLAY_KEYS = (
    "vector_id",
    "technique_id",
    "name",
    "one_liner",
    "category",
    "rail",
    "lifecycle_stage",
    "genai_modality",
    "social_surface",
    "control_bypassed",
    "actor_type",
    "economic_class",
    "is_authorized_push",
    "generate_mode",
    "simulatable_signals",
    "simulator",
    "features_expected",
    "entities",
    "novelty_notes",
    "vector_class",
    "corroboration_type",
    "dual_use_rating",
    "confidence_level",
)

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


def normalize_groq_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Map free-text LLM labels to AttackSpec enum strings."""
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


def _resolve_injector_id(technique_id: str, simulator: dict[str, Any] | None) -> str:
    sim = simulator or {}
    raw_id = sim.get("injector_id")
    if raw_id:
        resolved = _coerce_enum(raw_id, _VALID_INJECTORS, _INJECTOR_ALIASES)
        if resolved:
            return resolved
        lower = str(raw_id).lower()
        if any(k in lower for k in ("identity", "kyc", "liveness", "deepfake", "vkyc")):
            return "identity_trajectory"
        if "mule" in lower or "graph" in lower:
            return "graph_mule"
        if "session" in lower or "app" in lower:
            return "app_session"
        if "beneficiary" in lower or "invoice" in lower or "doc" in lower:
            return "doc_beneficiary"
    tid = technique_id.upper()
    if tid in _TECHNIQUE_DEFAULTS:
        return _TECHNIQUE_DEFAULTS[tid][1]
    return "identity_trajectory"


def _sanitize_simulator_and_signals(merged: dict[str, Any], base_signals: dict[str, Any]) -> None:
    tid = str(merged.get("technique_id", "")).upper()
    injector = _resolve_injector_id(tid, merged.get("simulator"))
    param_schema = (merged.get("simulator") or {}).get("param_schema") or {}
    merged["simulator"] = {"injector_id": injector, "param_schema": param_schema}

    if merged.get("generate_mode") == "name_only":
        return

    signals = dict(base_signals)
    groq_signals = merged.get("simulatable_signals")
    if isinstance(groq_signals, dict):
        signals.update(groq_signals)
    try:
        merged["simulatable_signals"] = validate_simulatable_signals(injector, signals)
    except Exception:
        try:
            merged["simulatable_signals"] = validate_simulatable_signals(injector, base_signals)
        except Exception:
            merged["generate_mode"] = "name_only"
            merged["simulatable_signals"] = {}


def _env_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _groq_disabled() -> bool:
    from packages.agents.settings import get_agent_settings

    settings = get_agent_settings()
    if settings.groq_disabled:
        return True
    return os.getenv("GROQ_DISABLED", "").lower() in {"1", "true", "yes"}


def _groq_api_key() -> str:
    if _groq_disabled():
        return ""
    from packages.agents.settings import get_agent_settings

    settings = get_agent_settings()
    if settings.groq_api_key:
        return settings.groq_api_key
    # Fallback parse (e.g. scripts without pydantic env)
    key = os.getenv("GROQ_API_KEY", "")
    if key:
        return key
    if _env_file_path().is_file():
        for line in _env_file_path().read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("GROQ_API_KEY="):
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _groq_chat_url() -> str:
    from packages.agents.settings import get_agent_settings

    base = get_agent_settings().groq_api_base.rstrip("/")
    return f"{base}/chat/completions"


def _groq_models_to_try() -> list[str]:
    from packages.agents.settings import get_agent_settings

    settings = get_agent_settings()
    ordered: list[str] = []
    for model in (settings.groq_model, *GROQ_MODEL_FALLBACKS):
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def _groq_retry_wait_seconds(response: httpx.Response, attempt: int) -> float:
    """Honor Retry-After when present; otherwise short exponential backoff."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 60.0)
        except ValueError:
            pass
    return min(5.0 * (2 ** attempt), 30.0)


def _groq_chat_completion(
    api_key: str,
    payload: dict[str, Any],
    models: list[str] | None = None,
) -> dict[str, Any]:
    """POST chat/completions; retry alternate models on 404; backoff on 429."""
    url = _groq_chat_url()
    last_error: str | None = None
    max_rate_retries = 3
    for model in models or _groq_models_to_try():
        for rate_attempt in range(max_rate_retries):
            attempt = {**payload, "model": model}
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=attempt,
                )
            if response.status_code < 400:
                return response.json()

            body = response.text[:500]
            last_error = f"model={model} status={response.status_code} body={body}"
            if response.status_code == 404:
                break  # try next model id
            if response.status_code == 429 and rate_attempt < max_rate_retries - 1:
                time.sleep(_groq_retry_wait_seconds(response, rate_attempt))
                continue
            raise httpx.HTTPStatusError(
                f"Groq API error: {last_error}",
                request=response.request,
                response=response,
            )

    raise RuntimeError(f"Groq API error (no model worked): {last_error}")


def _groq_message_text(message: dict[str, Any]) -> str:
    """GPT-OSS on Groq may leave content empty and put text in reasoning."""
    for key in ("content", "reasoning"):
        val = message.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _parse_llm_json(text: str) -> dict[str, Any]:
    """Parse JSON from model output (handles markdown fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    # First {...} block if model added prose around JSON
    if not cleaned.startswith("{") and "{" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if end > start:
            cleaned = cleaned[start : end + 1]
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM JSON root must be an object")
    if "attacks" in data and isinstance(data["attacks"], list):
        if not data["attacks"]:
            return data
        first = data["attacks"][0]
        if isinstance(first, dict):
            return first
    return data


def extract_attack_json(article_text: str, source_url: str, temperature: float = 0.1) -> dict[str, Any]:
    """LLM structured extraction with low temperature."""
    api_key = _groq_api_key()
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    prompt = (
        f"Extract one GenAI payment fraud attack vector from this allowlisted source.\n"
        f"Source URL: {source_url}\n\nArticle:\n{article_text[:6000]}\n\n{_EXTRACTION_SCHEMA_HINT}"
    )
    base_messages = [
        {
            "role": "system",
            "content": (
                "You extract payment fraud typology for a bank defense lab. "
                "Respond with a single JSON object only, no markdown."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    last_error: Exception | None = None
    for json_mode in (True, False):
        payload: dict[str, Any] = {
            "temperature": min(temperature, 0.2),
            "max_tokens": 2048,
            "messages": base_messages,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            data = _groq_chat_completion(api_key, payload)
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if json_mode and exc.response is not None and exc.response.status_code == 400:
                continue
            raise
        message = data.get("choices", [{}])[0].get("message", {})
        content = _groq_message_text(message)
        if not content:
            last_error = ValueError("Groq returned empty message content")
            continue
        try:
            return _parse_llm_json(content)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            continue
    raise ValueError(f"Groq JSON parse failed: {last_error}")


def rule_based_extract(article_text: str, source_url: str, source_domain: str) -> dict[str, Any]:
    """Deterministic extraction for fixtures / offline demos (no LLM)."""
    text = article_text.lower()
    from packages.osint.allowlist import tier_for_domain

    tier = tier_for_domain(source_domain)

    if "deepfake" in text and ("kyc" in text or "liveness" in text or "vkyc" in text):
        technique_id = "T09"
        category = 2
        rail = "onboarding"
        lifecycle = "onboarding_kyc"
        modality = "video"
        economic = "ATO"
        injector = "identity_trajectory"
        signals = {
            "seasoning_days": 0,
            "seasoning_txn_count": 0,
            "liveness_score": 0.35,
            "doc_consistency": 0.8,
            "device_hash_shift": False,
            "kyc_tier": "tier2",
        }
        name = "Deepfake VKYC liveness bypass (identified)"
    elif "upi" in text or "impersonation" in text or "authorized push" in text:
        technique_id = "T13"
        category = 3
        rail = "upi_like"
        lifecycle = "payment_initiation"
        modality = "voice"
        economic = "APP"
        injector = "app_session"
        signals = {
            "persuasion_labels": ["bank_impersonation", "urgency"],
            "call_active_flag": True,
            "copy_paste_payee_flag": True,
            "pause_ms": 4000,
            "new_payee": True,
            "urgency_pressure": 0.85,
        }
        name = "UPI impersonation APP (identified)"
    elif "mule" in text or "fan-in" in text or "cash-out" in text:
        technique_id = "T01"
        category = 1
        rail = "upi_like"
        lifecycle = "disbursement_mule"
        modality = "bot"
        economic = "mule"
        injector = "graph_mule"
        signals = {
            "fan_in_1h": 15,
            "fan_out_ttl_hours": 2.0,
            "smurf_cap_ratio": 0.9,
            "hop_rails": ["upi_like"],
            "mule_account_age_days": 7,
            "cashout_mcc_or_sink": "crypto_offramp",
        }
        name = "Mule fan-in funnel (identified)"
    else:
        technique_id = "T13"
        category = 3
        rail = "upi_like"
        lifecycle = "payment_initiation"
        modality = "text"
        economic = "APP"
        injector = "app_session"
        signals = {
            "persuasion_labels": ["impersonation"],
            "call_active_flag": False,
            "copy_paste_payee_flag": True,
            "pause_ms": 1000,
            "new_payee": True,
            "urgency_pressure": 0.7,
        }
        name = "Payment impersonation APP (identified)"

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

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    vector_id = f"identify-{slug}"

    spec: dict[str, Any] = {
        "vector_id": vector_id,
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
        "generate_mode": "generate",
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
    }
    from packages.catalog.features import enrich_spec_features

    return enrich_spec_features(spec)


def _slug_vector_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    return f"identify-{slug}"


def enrich_groq_extract(
    raw: dict[str, Any],
    article_text: str,
    source_url: str,
    source_domain: str,
) -> dict[str, Any]:
    """
    Merge Groq partial JSON onto a rule-based skeleton so AttackSpec validates.
    Compound models often return technique_id/name only.
    """
    raw = normalize_groq_raw(raw)
    base = rule_based_extract(article_text, source_url, source_domain)
    base_signals = base.get("simulatable_signals") or {}
    merged = dict(base)

    for key in _OVERLAY_KEYS:
        if key in {"simulator", "simulatable_signals"}:
            continue
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        if isinstance(val, list) and not val:
            continue
        merged[key] = val

    tid = str(merged.get("technique_id", "")).upper()
    if tid in _TECHNIQUE_DEFAULTS:
        cat, injector = _TECHNIQUE_DEFAULTS[tid]
        merged["technique_id"] = tid
        if merged.get("category") is None:
            merged["category"] = cat
        sim = merged.get("simulator") or {}
        if not sim.get("injector_id"):
            merged["simulator"] = {
                "injector_id": injector,
                "param_schema": sim.get("param_schema", {}),
            }
        if tid in {"T20", "T21", "T22", "T23"}:
            merged["generate_mode"] = "name_only"

    groq_name = (raw.get("name") or "").strip()
    if groq_name and "(identified)" not in groq_name:
        merged["name"] = groq_name
        if not raw.get("vector_id"):
            merged["vector_id"] = _slug_vector_id(groq_name)
    elif raw.get("technique_id"):
        merged["name"] = merged["name"].replace(" (identified)", "").strip()
        merged["vector_id"] = _slug_vector_id(merged["name"])
    if raw.get("one_liner"):
        merged["one_liner"] = raw["one_liner"]

    merged["extraction_source"] = "groq"
    _sanitize_simulator_and_signals(merged, base_signals)

    merged["source_urls"] = raw.get("source_urls") or [source_url]
    merged["status"] = "proposed"
    from packages.catalog.features import enrich_spec_features

    return enrich_spec_features(merged)


def extract_from_document(
    article_text: str,
    source_url: str,
    source_domain: str,
    max_retries: int = 2,
) -> dict[str, Any]:
    """LLM extraction with rule-based fallback."""
    groq_last_error: str | None = None
    if _groq_api_key():
        from pydantic import ValidationError

        from packages.catalog.models import AttackSpec

        for _ in range(max_retries):
            try:
                raw = extract_attack_json(article_text, source_url)
                enriched = enrich_groq_extract(raw, article_text, source_url, source_domain)
                enriched.setdefault("source_urls", [source_url])
                enriched["extraction_source"] = "groq"
                AttackSpec.model_validate(enriched)
                return enriched
            except httpx.HTTPStatusError as exc:
                groq_last_error = str(exc)[:240]
                if exc.response is not None and exc.response.status_code == 429:
                    time.sleep(_groq_retry_wait_seconds(exc.response, 0))
                    continue
                continue
            except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError, RuntimeError) as exc:
                groq_last_error = str(exc)[:240]
                continue
            except ValidationError as exc:
                groq_last_error = str(exc.errors()[0]["msg"])[:240]
                continue
    spec = rule_based_extract(article_text, source_url, source_domain)
    spec["extraction_source"] = "rules"
    if groq_last_error:
        spec["groq_last_error"] = groq_last_error
    return spec
