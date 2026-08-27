"""Embeddings for pgvector (384-d cosine). Default: fastembed ONNX, not torch."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

VECTOR_DIM = 384
_FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"
_ST_MODEL = "BAAI/bge-small-en-v1.5"


def embeddings_backend() -> str:
    raw = os.getenv("AEGIS_EMBEDDINGS", "").strip().lower()
    if raw in {"hash", "fastembed", "st", "sentence-transformers"}:
        if raw in {"st", "sentence-transformers"}:
            return "st"
        return raw
    if os.getenv("EMBEDDINGS_DISABLED", "").lower() in {"1", "true", "yes"}:
        return "hash"
    return "fastembed"


def _hash_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    vals = [digest[i % len(digest)] / 255.0 for i in range(VECTOR_DIM)]
    norm = sum(v * v for v in vals) ** 0.5 or 1.0
    return [v / norm for v in vals]


@lru_cache(maxsize=1)
def _fastembed_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=_FASTEMBED_MODEL)


@lru_cache(maxsize=1)
def _st_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_ST_MODEL)


def _fastembed_vector(text: str) -> list[float]:
    vec = next(_fastembed_model().embed([text]))
    out = [float(x) for x in vec]
    if len(out) != VECTOR_DIM:
        raise ValueError(f"fastembed dim {len(out)} != {VECTOR_DIM}")
    return out


def _st_vector(text: str) -> list[float]:
    vector = _st_model().encode(text, normalize_embeddings=True)
    out = vector.tolist()
    if len(out) != VECTOR_DIM:
        raise ValueError(f"sentence-transformers dim {len(out)} != {VECTOR_DIM}")
    return out


def embed_text(text: str) -> list[float]:
    """Return an L2-normalized 384-d vector for Postgres vector(384)."""
    backend = embeddings_backend()
    if backend == "hash":
        return _hash_embedding(text)
    if backend == "st":
        try:
            return _st_vector(text)
        except Exception:
            return _hash_embedding(text)
    try:
        return _fastembed_vector(text)
    except Exception:
        return _hash_embedding(text)


def dedup_key_text(name: str, rail: str, technique_id: str) -> str:
    return f"{name}|{rail}|{technique_id}"
