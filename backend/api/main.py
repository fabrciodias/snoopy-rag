from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings

from backend.api.translation import (
    router as translation_router,
)

from backend.api.routers.folders import (
    router as folders_router,
)

from backend.api.routers.documents import (
    router as documents_router,
)

from backend.api.routers.sync import (
    router as sync_router,
)

from backend.api.routers.operations import (
    router as operations_router,
)

from backend.api.routers.investigations import (
    router as investigations_router,
)


# ============================================================
# Application
# ============================================================

app = FastAPI(
    title="Snoopy-RAG V3 Alpha API",
    version="0.1.0",
)


# ============================================================
# API Routers
# ============================================================

app.include_router(
    translation_router
)

app.include_router(
    folders_router
)

app.include_router(
    documents_router
)

app.include_router(
    sync_router
)

app.include_router(
    operations_router
)

app.include_router(
    investigations_router
)


# ============================================================
# Frontend Configuration
# ============================================================

@app.get(
    "/config",
    tags=["Frontend"],
)
def frontend_config():
    """
    Retorna somente as configurações públicas necessárias
    para inicializar o cliente frontend.

    Nunca expõe SUPABASE_SERVICE_KEY ou qualquer segredo
    do backend.
    """

    return {
        "url": settings.supabase_url,
        "key": settings.supabase_key,
        "googleApiKey": settings.google_api_key,
        "googleAppId": settings.google_app_id,
    }


# ============================================================
# Frontend V3
# ============================================================

FRONTEND_DIR = (
    Path(__file__).resolve().parents[2]
    / "frontend"
)


@app.get(
    "/",
    include_in_schema=False,
)
def frontend_index():
    return FileResponse(
        FRONTEND_DIR / "app" / "index.html"
    )


app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
    ),
    name="frontend",
)
