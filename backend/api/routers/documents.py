from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
)

from backend.api.container import (
    doc_repo,
    evidence_repo,
    investigation_repo,
)

from backend.infrastructure.database import (
    supabase_client,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def _has_access_to_matching_document(
    document_hash: str,
    user_id: str,
) -> bool:
    """
    Verifica se o usuário possui acesso a uma cópia ativa
    e fisicamente idêntica ao documento de origem.

    O hash permite correlacionar cópias entre acervos,
    mas não substitui a verificação de autorização.
    """

    response = (
        supabase_client
        .table("documents")
        .select(
            "id, folder_id, document_hash, status"
        )
        .eq(
            "document_hash",
            document_hash,
        )
        .eq(
            "status",
            "ACTIVE",
        )
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


def _ensure_reading_access(
    source_document: dict,
    user_id: str,
) -> bool:
    """
    Autoriza a leitura quando o usuário possui acesso
    ao acervo original ou a uma cópia idêntica autorizada.

    Retorna True quando o acesso é direto à fonte original
    e False quando o acesso ocorre por uma cópia idêntica.

    A função não retorna metadados do acervo alternativo.
    """

    folder_id = source_document.get("folder_id")

    if not folder_id:
        raise HTTPException(
            status_code=404,
            detail="Documento não encontrado.",
        )

    try:
        ensure_folder_access(
            folder_id,
            user_id,
        )

        return True

    except HTTPException:
        pass

    document_hash = source_document.get(
        "document_hash"
    )

    if (
        not document_hash
        or not _has_access_to_matching_document(
            document_hash,
            user_id,
        )
    ):
        raise HTTPException(
            status_code=404,
            detail="Documento não encontrado.",
        )

    return False


@router.get("/{document_id}/reading")
def get_document_reading(
    document_id: str,
    evidence_id: str,
    authorization: str | None = Header(
        default=None,
    ),
):
    """
    Recupera a representação documental correspondente
    à evidência persistida.

    A representação é determinada pela proveniência da
    evidência, não pela versão atualmente publicada.

    A leitura pode ser autorizada pelo acesso à fonte
    original ou a uma cópia idêntica em um acervo autorizado.

    O link do Google Drive só é disponibilizado quando
    o usuário possui acesso direto à fonte original.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    # --------------------------------------------------------
    # 1. Recuperar a evidência persistida
    # --------------------------------------------------------

    evidence = evidence_repo.get_by_id(
        evidence_id
    )

    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    if evidence.document_id != document_id:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    # --------------------------------------------------------
    # 2. Validar a proveniência da evidência
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 3. Recuperar a investigação de origem
    # --------------------------------------------------------

    investigation = (
        investigation_repo.get_by_id(
            evidence.investigation_id
        )
    )

    if investigation is None:
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    # --------------------------------------------------------
    # 4. Recuperar a fonte documental original
    # --------------------------------------------------------

    source_response = (
        supabase_client
        .table("documents")
        .select(
            """
            id,
            folder_id,
            title,
            document_hash
            """
        )
        .eq(
            "id",
            evidence.document_id,
        )
        .limit(1)
        .execute()
    )

    if not source_response.data:
        raise HTTPException(
            status_code=404,
            detail="Documento não encontrado.",
        )

    source_document = source_response.data[0]

    # A fonte precisa pertencer ao acervo registrado
    # na investigação que originou a evidência.
    if (
        source_document.get("folder_id")
        != investigation.folder_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Evidência não encontrada.",
        )

    # --------------------------------------------------------
    # 5. Verificar autorização de leitura
    # --------------------------------------------------------

    has_original_access = _ensure_reading_access(
        source_document,
        user_id,
    )

    # --------------------------------------------------------
    # 6. Recuperar a representação histórica correta
    # --------------------------------------------------------

    representation_id = (
        provenance.representation_id
    )

    if not representation_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "A representação de origem da evidência "
                "não está disponível."
            ),
        )

    try:
        representation = (
            doc_repo.get_representation_by_id(
                document_id=evidence.document_id,
                representation_id=representation_id,
            )
        )

    except RuntimeError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível validar a representação "
                "documental de origem."
            ),
        )

    if representation is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "A representação de origem da evidência "
                "não está mais disponível."
            ),
        )

    # Defesa adicional: não aceitar uma representação
    # cuja identidade não corresponda à proveniência.
    if (
        representation.document_id
        != evidence.document_id
        or representation.representation_id
        != representation_id
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "A representação de origem da evidência "
                "não foi encontrada."
            ),
        )

    # --------------------------------------------------------
    # 7. Recuperar o link da representação histórica
    # --------------------------------------------------------

    metadata = (
        getattr(
            representation,
            "metadata",
            None,
        )
        or {}
    )

    drive_link = (
        metadata.get("drive_link")
        if isinstance(metadata, dict)
        else None
    )

    # Não expor o link da fonte original quando o acesso
    # à leitura foi autorizado somente por uma cópia.
    if not has_original_access:
        drive_link = None

    # --------------------------------------------------------
    # 8. Retornar os dados necessários à leitura
    # --------------------------------------------------------

    return {
        "document_id": evidence.document_id,
        "title": source_document.get("title"),
        "drive_link": drive_link,
        "evidence_id": evidence.evidence_id,
        "representation_id": representation_id,
        "location": evidence.location,
        "representation": representation,
    }


@router.get("/{document_id}")
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

    A representação retornada é sempre a representação
    atualmente publicada para o documento.

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
            current_representation_id
            """
        )
        .eq(
            "id",
            document_id,
        )
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

    representation_id = (
        document.get("current_representation_id")
    )

    current_representation = None

    if representation_id:
        representation_response = (
            supabase_client
            .table("document_representations")
            .select(
                "id, document_id, representation"
            )
            .eq(
                "id",
                representation_id,
            )
            .eq(
                "document_id",
                document_id,
            )
            .limit(1)
            .execute()
        )

        if not representation_response.data:
            raise HTTPException(
                status_code=500,
                detail=(
                    "A representação corrente do documento "
                    "não foi encontrada."
                ),
            )

        representation_record = (
            representation_response.data[0]
        )

        current_representation = (
            representation_record.get(
                "representation"
            )
        )

    return {
        "id": document["id"],
        "folder_id": document["folder_id"],
        "title": document["title"],
        "authors": document["authors"],
        "publication_year": document["publication_year"],
        "drive_file_id": document["drive_file_id"],
        "drive_link": document["drive_link"],
        "status": document["status"],
        "current_representation_id": (
            representation_id
        ),
        "current_representation": (
            current_representation
        ),
    }