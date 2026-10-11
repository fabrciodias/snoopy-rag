from fastapi import APIRouter, Header, HTTPException

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
)
from backend.api.container import (
    evidence_repo,
    investigation_repo,
)
from backend.infrastructure.database import supabase_client


router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"],
)


def _has_access_to_matching_document(
    document_hash: str,
    user_id: str,
) -> bool:
    """
    Verifica se o usuário possui acesso a um documento ativo
    com o mesmo hash físico da fonte da evidência.

    O hash permite correlacionar cópias do mesmo arquivo
    entre acervos diferentes, mas não substitui a autorização.
    """

    response = (
        supabase_client
        .table("documents")
        .select("id, folder_id, document_hash, status")
        .eq("document_hash", document_hash)
        .eq("status", "ACTIVE")
        .execute()
    )

    for document in response.data or []:
        folder_id = document.get("folder_id")

        if not folder_id:
            continue

        try:
            ensure_folder_access(
                folder_id,
                user_id,
            )
        except HTTPException:
            continue

        return True

    return False


@router.get("/{evidence_id}")
def get_evidence(
    evidence_id: str,
    authorization: str | None = Header(
        default=None,
    ),
):
    """
    Recupera a evidência persistida pela identidade estável.

    Outro usuário pode recuperar a mesma evidência quando
    possui acesso à fonte documental correspondente, mesmo
    que a cópia esteja em outro acervo e tenha outro document_id.

    A recuperação não refaz a busca nem depende do estado local
    do frontend.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    evidence = evidence_repo.get_by_id(
        evidence_id
    )

    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    investigation = investigation_repo.get_by_id(
        evidence.investigation_id
    )

    if investigation is None:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    # Verifica a consistência entre a evidência e sua proveniência.
    provenance = evidence.provenance

    if (
        provenance.investigation_id
        != evidence.investigation_id
        or provenance.document_id
        != evidence.document_id
        or provenance.unit_id
        != evidence.unit_id
        or provenance.location
        != evidence.location
    ):
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    # Recupera a fonte documental original da evidência.
    source_response = (
        supabase_client
        .table("documents")
        .select(
            "id, folder_id, document_hash, status"
        )
        .eq("id", evidence.document_id)
        .limit(1)
        .execute()
    )

    if not source_response.data:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    source_document = source_response.data[0]

    # A fonte precisa pertencer ao acervo registrado na investigação
    # que originou a evidência.
    if (
        source_document.get("folder_id")
        != investigation.folder_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    # Primeiro, verifica se o usuário pode acessar o acervo original.
    # Não exigimos que ele seja o proprietário da investigação.
    try:
        ensure_folder_access(
            source_document["folder_id"],
            user_id,
        )
        source_is_accessible = True

    except HTTPException:
        source_is_accessible = False

    # Se não houver acesso ao acervo original, verifica se existe
    # uma cópia idêntica em algum acervo autorizado ao solicitante.
    if not source_is_accessible:
        document_hash = source_document.get("document_hash")

        if (
            not document_hash
            or not _has_access_to_matching_document(
                document_hash,
                user_id,
            )
        ):
            raise HTTPException(
                status_code=404,
                detail="Evidência não encontrada.",
            )

    # Retorna a evidência persistida original.
    # Não refaz a recuperação nem cria outra evidência.
    return evidence