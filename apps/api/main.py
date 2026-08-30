"""FastAPI application for AegisLoop lab."""

from apps.api.env import load_project_env

load_project_env()

from apps.api.logging_config import configure_logging

configure_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.db import init_db
from apps.api.routes.catalog import router as catalog_router
from apps.api.routes.defend import router as defend_router
from apps.api.routes.demo import router as demo_router
from apps.api.routes.generate import router as generate_router
from apps.api.routes.identify import router as identify_router
from packages.agents.llm import public_llm_status
from packages.osint.settings import get_osint_settings

app = FastAPI(title="AegisLoop API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog_router)
app.include_router(identify_router)
app.include_router(generate_router)
app.include_router(defend_router)
app.include_router(demo_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    from sqlalchemy import text

    from apps.api.db import engine

    postgres_ok = False
    pgvector_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            postgres_ok = True
            row = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
            pgvector_ok = row is not None
    except Exception:
        postgres_ok = False
    osint = get_osint_settings()
    llm = public_llm_status()
    return {
        "status": "ok" if postgres_ok and pgvector_ok else "degraded",
        "postgres": postgres_ok,
        "pgvector": pgvector_ok,
        "identify_live_search": osint.identify_live_search,
        "tavily_configured": bool(osint.tavily_api_key),
        "llm": llm,
    }
