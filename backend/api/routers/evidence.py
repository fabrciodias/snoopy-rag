from fastapi import APIRouter, Header, HTTPException

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
)

from backend.api.container import (
    evidence_repo,
    investigation_repo,
)


router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"],
)


@router.get("/{evidence_id}")
def get_evidence(
    evidence_id: str,
    authorization: str | None = Header(
        default=None,
    ),
):
    """
    Recupera uma evidência pela identidade persistida.

    A autorização é realizada no backend, verificando
    a investigação associada e o acesso ao acervo.

    A recuperação não depende do estado local do frontend.
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

    if investigation.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    ensure_folder_access(
        investigation.folder_id,
        user_id,
    )

    return evidence