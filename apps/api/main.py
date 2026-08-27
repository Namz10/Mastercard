"""FastAPI application for AegisLoop lab."""

from apps.api.env import load_project_env

load_project_env()

from fastapi import FastAPI

from apps.api.routes.catalog import router as catalog_router
from apps.api.routes.defend import router as defend_router
from apps.api.routes.generate import router as generate_router
from apps.api.routes.identify import router as identify_router

app = FastAPI(title="AegisLoop API", version="0.1.0")

app.include_router(catalog_router)
app.include_router(identify_router)
app.include_router(generate_router)
app.include_router(defend_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
