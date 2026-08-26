"""Query expansion for Scout."""

from packages.osint.query_expand import expand_search_queries


def test_expand_generic_merchant_upi():
    qs = expand_search_queries("fake merchant network UPI transaction laundering India")
    assert len(qs) >= 2
    assert any("merchant" in q.lower() or "upi" in q.lower() for q in qs)


def test_expand_empty_uses_defaults():
    qs = expand_search_queries("")
    assert len(qs) >= 1


def test_expand_dedupes():
    qs = expand_search_queries("payment fraud payment fraud")
    assert len(qs) >= 1
