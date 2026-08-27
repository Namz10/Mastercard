"""Database configuration and schema bootstrap (Postgres + pgvector)."""

import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aegisloop:aegisloop@localhost:5432/aegisloop",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _register_vector(dbapi_conn, _connection_record) -> None:
    try:
        from pgvector.psycopg2 import register_vector

        register_vector(dbapi_conn)
    except Exception:
        pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_pgvector() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def init_db() -> None:
    ensure_pgvector()
    from apps.api import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
