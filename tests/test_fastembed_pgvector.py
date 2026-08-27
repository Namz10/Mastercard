"""fastembed → same Postgres vector(384) as catalog/OSINT chunks."""

from __future__ import annotations

import os

import pytest

from packages.agents.embeddings import VECTOR_DIM, _hash_embedding, embed_text
from packages.osint.vector_store import cosine_similarity, max_catalog_similarity, register_catalog_embedding, upsert_chunk

_CI = os.getenv("CI", "").lower() in {"1", "true", "yes"}


def test_vector_dim_is_pgvector_width():
    vec = embed_text("Deepfake VKYC liveness bypass on UPI onboarding")
    assert len(vec) == VECTOR_DIM == 384
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-5


@pytest.mark.skipif(_CI, reason="CI uses hash embeddings; run locally with AEGIS_EMBEDDINGS=fastembed")
def test_fastembed_paraphrase_beats_unrelated(monkeypatch):
    monkeypatch.setenv("AEGIS_EMBEDDINGS", "fastembed")
    monkeypatch.delenv("EMBEDDINGS_DISABLED", raising=False)
    pytest.importorskip("fastembed")

    text_a = "Deepfake video KYC liveness bypass during remote onboarding"
    a = embed_text(text_a)
    if a == _hash_embedding(text_a):
        pytest.skip("fastembed model unavailable; hash fallback active")

    b = embed_text("Synthetic media used to pass bank VKYC liveness checks")
    c = embed_text("Invoice GST checksum rewrite to a wrong beneficiary account")
    sim_para = cosine_similarity(a, b)
    sim_other = cosine_similarity(a, c)
    assert sim_para > sim_other
    assert sim_para > 0.4


@pytest.mark.skipif(_CI, reason="CI uses hash embeddings")
def test_fastembed_vectors_roundtrip_pgvector(postgres_required, monkeypatch):
    monkeypatch.setenv("AEGIS_EMBEDDINGS", "fastembed")
    monkeypatch.delenv("EMBEDDINGS_DISABLED", raising=False)
    pytest.importorskip("fastembed")
    probe = "Deepfake VKYC liveness bypass"
    if embed_text(probe) == _hash_embedding(probe):
        pytest.skip("fastembed model unavailable")
    register_catalog_embedding(probe, "onboarding", "T09", vector_id="fastembed-t09")
    same = max_catalog_similarity(probe, "onboarding", "T09")
    assert same >= 0.99
    chunk = upsert_chunk(
        url="https://www.fincen.gov/fastembed-test",
        text="Deepfake VKYC liveness bypass during remote onboarding.",
        domain="fincen.gov",
        source_type="test",
    )
    assert chunk.id
