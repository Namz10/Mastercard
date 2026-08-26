"""Text embeddings for dedup (BAAI/bge-small-en-v1.5) with offline fallback."""

import hashlib
import os
from functools import lru_cache

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_VECTOR_DIM = 384


def _embeddings_disabled() -> bool:
    return os.getenv("EMBEDDINGS_DISABLED", "").lower() in {"1", "true", "yes"}


def _hash_embedding(text: str) -> list[float]:
    """Deterministic pseudo-embedding for tests / offline (no HF download)."""
    digest = hashlib.sha256(text.encode()).digest()
    vals = [digest[i % len(digest)] / 255.0 for i in range(_VECTOR_DIM)]
    norm = sum(v * v for v in vals) ** 0.5 or 1.0
    return [v / norm for v in vals]


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    if _embeddings_disabled():
        return _hash_embedding(text)
    try:
        model = _get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    except Exception:
        return _hash_embedding(text)


def dedup_key_text(name: str, rail: str, technique_id: str) -> str:
    return f"{name}|{rail}|{technique_id}"
