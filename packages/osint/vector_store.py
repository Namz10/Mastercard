"""Postgres pgvector store for OSINT chunks and catalog dedup embeddings."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from packages.agents.embeddings import embed_text

COLLECTION_NAME = "osint_chunks"
DEDUP_THRESHOLD = 0.92


@dataclass
class ChunkRecord:
    id: str
    url: str
    text: str
    domain: str
    source_type: str
    date: str


def _session():
    from apps.api.db import SessionLocal, init_db

    init_db()
    return SessionLocal()


def upsert_chunk(
    url: str,
    text: str,
    domain: str,
    source_type: str = "osint",
    date: str | None = None,
) -> ChunkRecord:
    from apps.api.models import OsintChunk

    chunk_id = str(uuid.uuid4())
    date_str = date or datetime.now(timezone.utc).isoformat()
    vector = embed_text(text[:2000])
    db = _session()
    try:
        row = OsintChunk(
            id=chunk_id,
            url=url,
            domain=domain,
            source_type=source_type,
            date=date_str,
            text=text[:4000],
            embedding=vector,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()
    return ChunkRecord(
        id=chunk_id,
        url=url,
        text=text,
        domain=domain,
        source_type=source_type,
        date=date_str,
    )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def max_catalog_similarity(name: str, rail: str, technique_id: str) -> float:
    """Max cosine similarity vs catalog_embeddings (pgvector cosine distance)."""
    from apps.api.db import engine, init_db

    init_db()
    key = embed_text(f"{name}|{rail}|{technique_id}")
    vec_literal = "[" + ",".join(str(float(x)) for x in key) + "]"
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1 - (embedding <=> CAST(:vec AS vector)) AS sim
                FROM catalog_embeddings
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT 1
                """
            ),
            {"vec": vec_literal},
        ).fetchone()
    if not row or row[0] is None:
        return 0.0
    return float(row[0])


def nearest_catalog_row(name: str, rail: str, technique_id: str) -> dict[str, Any] | None:
    from apps.api.db import engine, init_db

    init_db()
    key = embed_text(f"{name}|{rail}|{technique_id}")
    vec_literal = "[" + ",".join(str(float(x)) for x in key) + "]"
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT vector_id, name, rail, technique_id,
                       1 - (embedding <=> CAST(:vec AS vector)) AS sim
                FROM catalog_embeddings
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT 1
                """
            ),
            {"vec": vec_literal},
        ).fetchone()
    if not row:
        return None
    return {
        "vector_id": row[0],
        "name": row[1],
        "rail": row[2],
        "technique_id": row[3],
        "similarity": float(row[4]),
    }


def register_catalog_embedding(
    name: str,
    rail: str,
    technique_id: str,
    vector_id: str | None = None,
) -> None:
    from apps.api.models import CatalogEmbedding

    vid = vector_id or str(uuid.uuid4())
    vector = embed_text(f"{name}|{rail}|{technique_id}")
    db = _session()
    try:
        existing = db.get(CatalogEmbedding, vid)
        if existing:
            existing.name = name
            existing.rail = rail
            existing.technique_id = technique_id
            existing.embedding = vector
        else:
            db.add(
                CatalogEmbedding(
                    vector_id=vid,
                    name=name,
                    rail=rail,
                    technique_id=technique_id,
                    embedding=vector,
                )
            )
        db.commit()
    finally:
        db.close()


def clear_vector_tables() -> None:
    """Test helper: wipe embedding tables (real SQL, not a mock)."""
    from apps.api.models import CatalogEmbedding, OsintChunk

    db = _session()
    try:
        db.query(OsintChunk).delete()
        db.query(CatalogEmbedding).delete()
        db.commit()
    finally:
        db.close()


# Back-compat name used by older tests
def clear_memory_store() -> None:
    clear_vector_tables()
