from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    Header,
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel, Field


from backend.config import settings


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
# 2. Constantes da aplicação
# ============================================================

PUBLIC_FOLDER_ID = (
    "f7faf7d9-ec80-46c6-9572-174865bf1e62"
)


# ============================================================
# 3. Infraestrutura
# ============================================================

operation_repo = SupabaseOperationRepository(
    supabase_client
)

emb_provider = GeminiEmbeddingProvider()

investigation_repo = SupabaseInvestigationRepository(
    supabase_client
)

retrieval_result_repo = (
    SupabaseRetrievalResultRepository(
        supabase_client
    )
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
# 4. Application Services
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
# 5. Autenticação e autorização
# ============================================================

def get_authenticated_user_id(
    authorization: str | None,
) -> str:
    """
    Valida o JWT do Supabase e retorna o ID do usuário
    autenticado.

    O identificador do usuário nunca deve ser confiado
    quando fornecido pelo cliente no corpo da requisição.
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
    )[1].strip()

    if not supabase_token:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido.",
        )

    try:
        user_response = (
            supabase_client.auth.get_user(
                supabase_token
            )
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Sessão Supabase inválida.",
        )

    if not user_response.user:
        raise HTTPException(
            status_code=401,
            detail="Sessão Supabase inválida.",
        )

    return user_response.user.id


def ensure_folder_access(
    folder_id: str,
    user_id: str,
):
    """
    Verifica se o acervo existe, está ativo e pode ser
    acessado pelo usuário autenticado.

    Acesso permitido quando:

    1. o acervo pertence ao usuário autenticado; ou
    2. o acervo é o acervo público GEPAFOR.

    O acervo continua sendo a fronteira de autorização
    da V3 Alpha.
    """

    folder = (
        supabase_client
        .table("folders")
        .select(
            "id, user_id, name, drive_id, is_active"
        )
        .eq("id", folder_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not folder.data:
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    record = folder.data[0]

    if (
        record["id"] != PUBLIC_FOLDER_ID
        and record.get("user_id") != user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    return record


# ============================================================
# 6. Configuração pública do Frontend
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
# 7. Modelos de Entrada
# ============================================================

class DriveSyncRequest(BaseModel):
    folder_id: str
    google_token: str


class InvestigateRequest(BaseModel):
    folder_id: str
    query: str
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )


class FolderCreateRequest(BaseModel):
    drive_id: str
    name: str


# ============================================================
# 8. Endpoints — Folders / Acervos
# ============================================================

@app.get(
    "/folders/",
    tags=["Folders"],
)
def list_folders(
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Retorna os acervos disponíveis para o usuário.

    Inclui:

    - o acervo público GEPAFOR;
    - os acervos privados pertencentes ao usuário.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    response = (
        supabase_client
        .table("folders")
        .select(
            "id, user_id, name, drive_id, is_active, created_at"
        )
        .eq("is_active", True)
        .or_(
            f"user_id.eq.{user_id},"
            f"id.eq.{PUBLIC_FOLDER_ID}"
        )
        .order("created_at")
        .execute()
    )

    return response.data


@app.post(
    "/folders/",
    tags=["Folders"],
)
def create_folder(
    request: FolderCreateRequest,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Registra um acervo selecionado pelo Google Picker.

    A pasta do Drive pertence ao usuário autenticado.
    O frontend nunca escolhe o user_id.

    Se a pasta já estiver registrada para esse usuário,
    ela é reativada e seu nome é atualizado.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    drive_id = request.drive_id.strip()
    name = request.name.strip()

    if not drive_id:
        raise HTTPException(
            status_code=400,
            detail="drive_id não pode ser vazio.",
        )

    if not name:
        raise HTTPException(
            status_code=400,
            detail="name não pode ser vazio.",
        )

    try:
        response = (
            supabase_client
            .table("folders")
            .upsert(
                {
                    "user_id": user_id,
                    "drive_id": drive_id,
                    "name": name,
                    "is_active": True,
                },
                on_conflict="user_id,drive_id",
            )
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Falha ao registrar o acervo.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.delete(
    "/folders/{folder_id}",
    tags=["Folders"],
)
def delete_folder(
    folder_id: str,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Desativa logicamente um acervo privado.

    O acervo público GEPAFOR não pode ser removido.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    if folder_id == PUBLIC_FOLDER_ID:
        raise HTTPException(
            status_code=403,
            detail="O acervo público não pode ser removido.",
        )

    folder = (
        supabase_client
        .table("folders")
        .select(
            "id, user_id, is_active"
        )
        .eq("id", folder_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not folder.data:
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    record = folder.data[0]

    if record.get("user_id") != user_id:
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    response = (
        supabase_client
        .table("folders")
        .update({
            "is_active": False,
        })
        .eq("id", folder_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Falha ao desativar o acervo.",
        )

    return {
        "id": folder_id,
        "is_active": False,
    }


# ============================================================
# 9. Endpoints — Documents / Reading
# ============================================================

@app.get(
    "/documents/{document_id}",
    tags=["Documents"],
)
def get_document(
    document_id: str,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Retorna os dados necessários para a leitura de um
    documento no frontend.

    A autorização é realizada através do acervo ao qual
    o documento pertence.

    O frontend não acessa diretamente o banco.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    response = (
        supabase_client
        .table("documents")
        .select(
            """
            id,
            folder_id,
            title,
            authors,
            publication_year,
            drive_file_id,
            drive_link,
            status,
            representation
            """
        )
        .eq("id", document_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Documento não encontrado.",
        )

    document = response.data[0]

    ensure_folder_access(
        document["folder_id"],
        user_id,
    )

    return document


# ============================================================
# 10. Endpoints — Google Drive / Document Processing
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

    user_id = get_authenticated_user_id(
        authorization
    )

    folder = ensure_folder_access(
        request.folder_id,
        user_id,
    )

    # O acervo público é somente para leitura.
    # Ele não pode receber sincronização através da
    # identidade de um usuário.
    if request.folder_id == PUBLIC_FOLDER_ID:
        raise HTTPException(
            status_code=403,
            detail="O acervo público não pode ser sincronizado pelo frontend.",
        )

    if not folder.get("drive_id"):
        raise HTTPException(
            status_code=400,
            detail="O acervo não possui uma pasta do Google Drive vinculada.",
        )

    try:
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
# 11. Endpoints — Operations
# ============================================================

@app.get(
    "/operations/{operation_id}",
    tags=["Operations"],
)
def get_operation(
    operation_id: str,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Retorna o estado autoritativo de uma operação.

    O acesso é autorizado a partir do acervo associado
    à operação, evitando exposição de operações de outros
    usuários.

    O frontend pode utilizar este endpoint para polling
    e revalidação após perda de comunicação.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    operation = operation_service.get_operation_state(
        operation_id
    )

    if not operation:
        raise HTTPException(
            status_code=404,
            detail="Operação não encontrada.",
        )

    if not operation.target_id:
        raise HTTPException(
            status_code=500,
            detail="Operação sem acervo associado.",
        )

    ensure_folder_access(
        operation.target_id,
        user_id,
    )

    return operation


# ============================================================
# 12. Endpoints — History
# ============================================================

@app.get(
    "/history/",
    tags=["History"],
)
def list_history(
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Retorna o histórico recente de investigações
    pertencentes ao usuário autenticado.

    O histórico é auxiliar à experiência da aplicação.
    Não constitui a fonte de verdade de uma Investigation.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    response = (
        supabase_client
        .table("search_history")
        .select(
            "query, created_at"
        )
        .eq(
            "user_id",
            user_id,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(15)
        .execute()
    )

    seen = set()
    history = []

    for item in response.data or []:
        query = (
            item.get("query") or ""
        ).strip()

        if not query:
            continue

        if query in seen:
            continue

        seen.add(query)

        history.append({
            "query": query,
            "created_at": item.get(
                "created_at"
            ),
        })

    return history


# ============================================================
# 13. Endpoints — Investigation
# ============================================================

@app.post(
    "/investigate/",
    tags=["Investigation"],
)
def investigate(
    request: InvestigateRequest,
    authorization: str | None = Header(
        default=None
    ),
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

    O usuário é obtido exclusivamente do JWT autenticado.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    ensure_folder_access(
        request.folder_id,
        user_id,
    )

    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="A consulta não pode ser vazia.",
        )

    try:

        # ----------------------------------------------------
        # 1. Recuperação Híbrida
        # ----------------------------------------------------

        investigation, results = (
            retrieval_service.search(
                user_id=user_id,
                folder_id=request.folder_id,
                query=query,
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
        # 4. Histórico
        #
        # O histórico é persistido somente depois que a
        # investigação e a síntese terminaram com sucesso.
        #
        # Falha no histórico não invalida a investigação.
        # ----------------------------------------------------

        try:

            (
                supabase_client
                .table("search_history")
                .insert({
                    "user_id": user_id,
                    "folder_id": request.folder_id,
                    "query": query,
                })
                .execute()
            )

        except Exception:
            # Histórico é uma funcionalidade auxiliar.
            # Uma falha nessa persistência não deve transformar
            # uma investigação concluída em uma investigação
            # malsucedida.
            pass

        # ----------------------------------------------------
        # 5. Retorno
        # ----------------------------------------------------

        return {
            "investigation": investigation,
            "response": structured_response,
            "evidences": evidences,
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# 14. Frontend V3
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