"""FastAPI application for AegisLoop lab."""

from fastapi import FastAPI

from apps.api.routes.catalog import router as catalog_router

app = FastAPI(title="AegisLoop API", version="0.1.0")

app.include_router(catalog_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
