"""KillChain Atlas and pgvector embedding models."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db import Base

VECTOR_DIM = 384


class AtlasRow(Base):
    __tablename__ = "killchain_atlas"

    vector_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    technique_id: Mapped[str] = mapped_column(String(8), index=True)
    name: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), index=True)
    confidence_level: Mapped[str] = mapped_column(String(32))
    source_tier: Mapped[int] = mapped_column(Integer)
    generate_mode: Mapped[str] = mapped_column(String(16))
    category: Mapped[int] = mapped_column(Integer, index=True)
    spec: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OsintChunk(Base):
    __tablename__ = "osint_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(256), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM))


class CatalogEmbedding(Base):
    __tablename__ = "catalog_embeddings"

    vector_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    rail: Mapped[str] = mapped_column(String(64))
    technique_id: Mapped[str] = mapped_column(String(8), index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM))
