import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
)

from pydantic import BaseModel, Field

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
)

from backend.api.container import (
    retrieval_service,
    synthesis_service,
    operation_service,
    investigation_repo,
    evidence_repo,
)

from backend.domain.entities import (
    Investigation,
    InvestigationStatus,
    OperationProgress,
    OperationTargetType,
)

from backend.infrastructure.database import (
    supabase_client,
)


router = APIRouter(
    tags=["Investigation"],
)


class InvestigateRequest(BaseModel):
    folder_id: str
    query: str

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )


def _run_investigation(
    operation_id: str,
    investigation_id: str,
    user_id: str,
    folder_id: str,
    query: str,
    limit: int,
) -> None:
    """
    Executa a investigação em background.

    Operation registra a execução e seu progresso.
    Investigation mantém o estado persistente da investigação.
    """

    try:
        investigation = investigation_repo.get_by_id(
            investigation_id
        )

        if investigation is None:
            raise RuntimeError(
                "A investigação não pôde ser recuperada."
            )

        operation_service.update_progress(
            operation_id,
            OperationProgress(
                phase="retrieval",
                message="Recuperando evidências do acervo...",
            ),
        )

        investigation, results = retrieval_service.search(
            user_id=user_id,
            folder_id=folder_id,
            query=query,
            limit=limit,
            existing_investigation=investigation,
            finalize_status=False,
        )

        if not results:
            investigation_repo.update_status(
                investigation_id,
                InvestigationStatus.COMPLETED,
            )

            operation_service.complete_operation(
                operation_id,
                progress=OperationProgress(
                    phase="completed",
                    message=(
                        "Nenhuma evidência foi encontrada "
                        "no acervo para esta consulta."
                    ),
                ),
            )

            return

        operation_service.update_progress(
            operation_id,
            OperationProgress(
                phase="synthesis",
                message=(
                    "Produzindo síntese com base nas evidências..."
                ),
            ),
        )

        synthesis_service.synthesize(
            investigation=investigation,
            results=results,
        )

        operation_service.update_progress(
            operation_id,
            OperationProgress(
                phase="finalizing",
                message="Finalizando investigação...",
            ),
        )

        # O histórico é auxiliar.
        # Sua falha não invalida uma investigação concluída.
        try:
            (
                supabase_client
                .table("search_history")
                .insert({
                    "user_id": user_id,
                    "folder_id": folder_id,
                    "query": query,
                    "investigation_id": investigation_id,
                })
                .execute()
            )

        except Exception:
            pass

        operation_service.complete_operation(
            operation_id,
            progress=OperationProgress(
                phase="completed",
                message="Investigação concluída.",
            ),
        )

    except Exception as error:

        print(
            "[INVESTIGATION] Falha ao executar investigação "
            f"{investigation_id}: {error}"
        )

        try:
            investigation_repo.update_status(
                investigation_id,
                InvestigationStatus.FAILED,
            )

        except Exception as status_error:
            print(
                "[INVESTIGATION] Falha ao atualizar estado "
                f"da investigação: {status_error}"
            )

        try:
            operation_service.fail_operation(
                operation_id,
                str(error),
                progress=OperationProgress(
                    phase="failed",
                    message="A investigação não pôde ser concluída.",
                ),
            )

        except Exception as operation_error:
            print(
                "[INVESTIGATION] Falha ao persistir estado "
                f"terminal da operação: {operation_error}"
            )


@router.get(
    "/history/",
    tags=["History"],
)
def list_history(
    folder_id: str,
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

    ensure_folder_access(
        folder_id,
        user_id,
    )

    response = (
        supabase_client
        .table("search_history")
        .select(
            "query, created_at, investigation_id"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "folder_id",
            folder_id,
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
            "investigation_id": item.get(
                "investigation_id"
            ),
        })

    return history


@router.post(
    "/investigate/",
    tags=["Investigation"],
    status_code=202,
)
def investigate(
    request: InvestigateRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Cria uma investigação e inicia sua execução assíncrona.

    O frontend recebe os identificadores da execução.
    O estado da operação permanece recuperável pela API.
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

    investigation = None

    try:
        investigation = investigation_repo.create(
            Investigation(
                investigation_id=str(uuid.uuid4()),
                user_id=user_id,
                folder_id=request.folder_id,
                original_query=query,
                status=InvestigationStatus.PROCESSING,
                created_at=datetime.now(timezone.utc),
            )
        )

        operation = operation_service.start_operation(
            operation_type="INVESTIGATION",
            target_type=OperationTargetType.INVESTIGATION,
            target_id=investigation.investigation_id,
            progress=OperationProgress(
                phase="starting",
                message="Preparando investigação...",
            ),
        )

        if (
            not investigation.investigation_id
            or not operation.operation_id
        ):
            raise RuntimeError(
                "Não foi possível identificar a investigação "
                "e sua operação."
            )

    except Exception as error:
        if (
            investigation is not None
            and investigation.investigation_id
        ):
            try:
                investigation_repo.update_status(
                    investigation.investigation_id,
                    InvestigationStatus.FAILED,
                )
            except Exception:
                pass

        print(
            "[INVESTIGATION] Falha ao iniciar investigação: "
            f"{error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível iniciar a investigação.",
        ) from error

    background_tasks.add_task(
        _run_investigation,
        operation.operation_id,
        investigation.investigation_id,
        user_id,
        request.folder_id,
        query,
        request.limit,
    )

    return {
        "operation_id": operation.operation_id,
        "investigation_id": investigation.investigation_id,
        "status": operation.status,
    }


@router.get(
    "/investigations/{investigation_id}",
    tags=["Investigation"],
)
def get_investigation(
    investigation_id: str,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Recupera uma investigação persistida.

    O acesso depende da identidade do usuário e do
    acesso atual ao acervo associado à investigação.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    investigation = investigation_repo.get_by_id(
        investigation_id
    )

    if investigation is None:
        raise HTTPException(
            status_code=404,
            detail="Investigação não encontrada.",
        )

    if investigation.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Investigação não encontrada.",
        )

    try:
        ensure_folder_access(
            investigation.folder_id,
            user_id,
        )

    except HTTPException as error:
        if error.status_code in (403, 404):
            raise HTTPException(
                status_code=404,
                detail="Investigação não encontrada.",
            ) from None

        raise

    evidences = evidence_repo.get_by_investigation(
        investigation_id
    )

    response = investigation.structured_response

    return {
        "investigation": investigation,
        "response": response,
        "evidences": evidences,
    }