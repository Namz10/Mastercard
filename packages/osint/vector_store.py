"""Qdrant osint_chunks collection + in-memory fallback."""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from packages.agents.embeddings import embed_text

COLLECTION_NAME = "osint_chunks"
_MEMORY_STORE: list[dict[str, Any]] = []


@dataclass
class ChunkRecord:
    id: str
    url: str
    text: str
    domain: str
    source_type: str
    date: str


def _qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def _use_qdrant() -> bool:
    return os.getenv("QDRANT_DISABLED", "").lower() not in {"1", "true", "yes"}


def _get_client():
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    client = QdrantClient(url=_qdrant_url(), check_compatibility=False)
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    return client


def upsert_chunk(
    url: str,
    text: str,
    domain: str,
    source_type: str = "osint",
    date: str | None = None,
) -> ChunkRecord:
    """Embed and store a text chunk."""
    chunk_id = str(uuid.uuid4())
    date_str = date or datetime.now(timezone.utc).isoformat()
    vector = embed_text(text[:2000])

    payload = {
        "url": url,
        "date": date_str,
        "source_type": source_type,
        "domain": domain,
        "text": text[:4000],
    }

    if _use_qdrant():
        try:
            client = _get_client()
            from qdrant_client.models import PointStruct

            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=chunk_id, vector=vector, payload=payload)],
            )
        except Exception:
            _MEMORY_STORE.append({"id": chunk_id, "vector": vector, "payload": payload})
    else:
        _MEMORY_STORE.append({"id": chunk_id, "vector": vector, "payload": payload})

    return ChunkRecord(
        id=chunk_id,
        url=url,
        text=text,
        domain=domain,
        source_type=source_type,
        date=date_str,
    )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot  # vectors are normalized


def max_catalog_similarity(name: str, rail: str, technique_id: str) -> float:
    """Max cosine similarity vs in-memory catalog embedding keys."""
    key = embed_text(f"{name}|{rail}|{technique_id}")
    best = 0.0
    for row in _MEMORY_STORE:
        payload = row.get("payload", {})
        if payload.get("source_type") != "catalog_dedup":
            continue
        sim = cosine_similarity(key, row["vector"])
        if sim > best:
            best = sim
    return best


def register_catalog_embedding(name: str, rail: str, technique_id: str) -> None:
    vector = embed_text(f"{name}|{rail}|{technique_id}")
    _MEMORY_STORE.append(
        {
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": {
                "source_type": "catalog_dedup",
                "name": name,
                "rail": rail,
                "technique_id": technique_id,
            },
        }
    )


def clear_memory_store() -> None:
    _MEMORY_STORE.clear()
