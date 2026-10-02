from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
)

from backend.infrastructure.database import (
    supabase_client,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


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
