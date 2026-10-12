from pathlib import Path

from fastapi import FastAPI, HTTPException
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

from backend.api.routers.evidence import (
    router as evidence_router,
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

app.include_router(
    evidence_router
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
# Frontend de produção
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

FRONTEND_DIST_DIR = (
    PROJECT_ROOT
    / "frontend"
    / "dist"
)


@app.get(
    "/",
    include_in_schema=False,
)
def frontend_index():
    """
    Serve a página inicial da distribuição compilada do Vue.

    O frontend precisa ser compilado antes de a aplicação
    ser disponibilizada para uso.
    """

    index_path = (
        FRONTEND_DIST_DIR
        / "index.html"
    )

    if not index_path.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "Frontend ainda não compilado. "
                "Execute `npm run build` na raiz "
                "do projeto."
            ),
        )

    return FileResponse(
        index_path
    )


# O diretório pode não existir durante a configuração inicial
# ou a execução dos testes. Nesse caso, a API continua podendo
# ser inicializada, mas a interface ficará indisponível até
# que o frontend seja compilado.
if FRONTEND_DIST_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(
            directory=FRONTEND_DIST_DIR,
            html=True,
        ),
        name="frontend",
    )