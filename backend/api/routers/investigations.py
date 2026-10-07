from fastapi import (
    APIRouter,
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
    investigation_repo,
    evidence_repo,
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


@router.get(
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
            "query, created_at, investigation_id"
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
            "investigation_id": item.get(
                "investigation_id"
            ),
        })

    return history


@router.post(
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
                    "investigation_id": investigation.investigation_id,
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
    Recupera uma investigação já concluída.

    A investigação é restaurada a partir do estado persistido,
    sem executar novamente a busca ou a síntese.
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

    evidences = evidence_repo.get_by_investigation(
        investigation_id
    )

    response = investigation.structured_response

    return {
        "investigation": investigation,
        "response": response,
        "evidences": evidences,
    }