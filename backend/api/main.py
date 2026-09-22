from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    Header,
)
from pydantic import BaseModel

from backend.infrastructure.supabase_repositories import (
    SupabaseOperationRepository,
    SupabaseDocumentRepository,
    SupabaseRetrievalUnitRepository,
    SupabaseInvestigationRepository,
    SupabaseRetrievalResultRepository,
    SupabaseEvidenceRepository,
)

from backend.infrastructure.gemini_provider import (
    GeminiEmbeddingProvider,
)

from backend.infrastructure.database import (
    supabase_client,
)

from backend.infrastructure.drive_provider import (
    GoogleDriveProvider,
)

from backend.application.drive_sync_service import (
    DriveSyncService,
)

from backend.application.operation_service import (
    OperationService,
)

from backend.application.retrieval_service import (
    RetrievalService,
)

from backend.application.synthesis_service import (
    SynthesisService,
)

from backend.application.document_processor import (
    DocumentProcessor,
)

from backend.application.segmentation_service import (
    SegmentationService,
)

from backend.application.publication_service import (
    PublicationService,
)


# ============================================================
# 1. Inicialização do App FastAPI
# ============================================================

app = FastAPI(
    title="Snoopy-RAG V3 Alpha API",
    version="0.1.0",
)


# ============================================================
# 2. Infraestrutura
# ============================================================

operation_repo = SupabaseOperationRepository(
    supabase_client
)

emb_provider = GeminiEmbeddingProvider()

investigation_repo = SupabaseInvestigationRepository(
    supabase_client
)

retrieval_result_repo = SupabaseRetrievalResultRepository(
    supabase_client
)

evidence_repo = SupabaseEvidenceRepository(
    supabase_client
)

doc_repo = SupabaseDocumentRepository(
    supabase_client
)

unit_repo = SupabaseRetrievalUnitRepository(
    supabase_client
)

drive_provider = GoogleDriveProvider()


# ============================================================
# 3. Application Services
# ============================================================

operation_service = OperationService(
    operation_repo
)

retrieval_service = RetrievalService(
    emb_provider,
    supabase_client,
    investigation_repo,
    retrieval_result_repo,
)

synthesis_service = SynthesisService(
    evidence_repo,
    investigation_repo,
)

doc_processor = DocumentProcessor()

seg_service = SegmentationService()

publication_service = PublicationService(
    processor=doc_processor,
    segmentation_service=seg_service,
    document_repo=doc_repo,
    unit_repo=unit_repo,
    embedding_provider=emb_provider,
)

drive_sync_service = DriveSyncService(
    client=supabase_client,
    drive_provider=drive_provider,
    operation_service=operation_service,
    publication_service=publication_service,
    document_repo=doc_repo,
    unit_repo=unit_repo,
)


# ============================================================
# 4. Modelos de Entrada
# ============================================================

class DriveSyncRequest(BaseModel):
    folder_id: str
    google_token: str


class InvestigateRequest(BaseModel):
    user_id: str
    folder_id: str
    query: str
    limit: int = 5


# ============================================================
# 5. Endpoints — Documents / Google Drive
# ============================================================

@app.post(
    "/sync-drive/",
    tags=["Documents"],
)
def sync_drive(
    request: DriveSyncRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Inicia a sincronização de um acervo do Google Drive.

    O JWT do Supabase identifica o usuário.
    O token do Google é utilizado pelo DriveProvider
    para acessar os arquivos do Drive.

    O processamento acontece em background e o estado
    autoritativo da execução fica registrado em Operation.
    """

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação não fornecido.",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Formato de autenticação inválido.",
        )

    supabase_token = authorization.split(
        " ",
        1,
    )[1]

    try:
        user_response = (
            supabase_client.auth.get_user(
                supabase_token
            )
        )

        if not user_response.user:
            raise HTTPException(
                status_code=401,
                detail="Sessão Supabase inválida.",
            )

        user_id = user_response.user.id

        operation = operation_service.start_operation(
            operation_type="DRIVE_SYNC",
            target_id=request.folder_id,
        )

        background_tasks.add_task(
            drive_sync_service.sync_folder,
            operation.operation_id,
            request.folder_id,
            user_id,
            request.google_token,
        )

        return {
            "operation_id": operation.operation_id,
            "status": operation.status,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# 6. Endpoints — Operations
# ============================================================

@app.get(
    "/operations/{operation_id}",
    tags=["Operations"],
)
def get_operation(
    operation_id: str,
):
    """
    Retorna o estado autoritativo de uma operação.

    Útil para revalidação caso a conexão SSE do frontend
    seja perdida.
    """

    operation = operation_service.get_operation_state(
        operation_id
    )

    if not operation:
        raise HTTPException(
            status_code=404,
            detail="Operação não encontrada.",
        )

    return operation


# ============================================================
# 7. Endpoints — Investigation
# ============================================================

@app.post(
    "/investigate/",
    tags=["Investigation"],
)
def investigate(
    request: InvestigateRequest,
):
    """
    Executa o fluxo completo de investigação:

    Recuperação Híbrida
        ↓
    RetrievalResults
        ↓
    Evidências
        ↓
    Síntese LLM
        ↓
    StructuredResponse
    """

    try:

        # ----------------------------------------------------
        # 1. Recuperação Híbrida
        # ----------------------------------------------------

        investigation, results = (
            retrieval_service.search(
                user_id=request.user_id,
                folder_id=request.folder_id,
                query=request.query,
                limit=request.limit,
            )
        )

        # ----------------------------------------------------
        # 2. Nenhum resultado
        # ----------------------------------------------------

        if not results:
            return {
                "message": (
                    "Nenhuma evidência encontrada no acervo "
                    "para esta busca."
                ),
                "investigation": investigation,
                "response": None,
                "evidences": [],
            }

        # ----------------------------------------------------
        # 3. Síntese baseada em evidências
        # ----------------------------------------------------

        structured_response, evidences = (
            synthesis_service.synthesize(
                investigation=investigation,
                results=results,
            )
        )

        # ----------------------------------------------------
        # 4. Retorno
        # ----------------------------------------------------

        return {
            "investigation": investigation,
            "response": structured_response,
            "evidences": evidences,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )