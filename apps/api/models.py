"""KillChain Atlas SQLAlchemy model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db import Base


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
