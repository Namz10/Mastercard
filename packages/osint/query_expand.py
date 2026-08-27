"""Expand user topics into allowlist-friendly Tavily queries."""

from packages.osint.search import DEFAULT_QUERY

# Typology hints → extra queries (payment fraud context on allowlisted sources)
_TOPIC_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("merchant", "collusion", "fake shop", "synthetic merchant"), "synthetic merchant collusion payment fraud"),
    (("upi", "vpa", "imps"), "RBI UPI authorized push payment fraud India"),
    (("india", "rbi", "nrcr"), "RBI payment fraud India regulator"),
    (("launder", "layering", "smurf", "structuring"), "money mule layering instant payment FinCEN"),
    (("mule", "fan-in", "fan-out", "cash-out", "cash out"), "FinCEN money mule funnel cash-out"),
    (("deepfake", "liveness", "vkyc", "kyc"), "FinCEN deepfake KYC liveness payment fraud"),
    (("imperson", "app", "authorized push", "social engineering"), "authorized push payment impersonation scam"),
    (("bec", "invoice", "beneficiary", "wire"), "business email compromise invoice beneficiary fraud"),
    (("card", "cnp", "bin", "testing"), "card fraud enumeration payment arxiv"),
    (("poison", "evasion", "adversarial", "detector"), "adversarial machine learning fraud detection arxiv"),
]


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in text.replace(",", " ").split() if len(w) > 2}


def expand_search_queries(topic: str, max_queries: int | None = 3) -> list[str]:
    """
    Turn a generic analyst prompt into Tavily queries with payment-fraud context.
    max_queries=0 or None → unlimited deduped list.
    """
    topic = (topic or "").strip()
    unlimited = max_queries is None or max_queries <= 0

    if not topic:
        queries = [
            DEFAULT_QUERY,
            "UPI authorized push payment impersonation India regulator",
        ]
        if unlimited:
            return queries
        return queries[:max_queries]

    lowered = topic.lower()
    queries: list[str] = [topic]

    if "fraud" not in lowered and "payment" not in lowered:
        queries.append(f"{topic} payment fraud")

    topic_kw = _keywords(topic)
    for hints, template in _TOPIC_HINTS:
        if topic_kw & set(hints):
            queries.append(f"{template} {topic}")

    if unlimited or len(queries) < (max_queries or 999):
        if "fincen" not in lowered:
            queries.append(f"FinCEN OR RBI payment fraud {topic}")

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = " ".join(q.split())
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)

    if unlimited:
        return out
    return out[:max_queries]

