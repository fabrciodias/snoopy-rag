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
            .eq("id", representation_id)
            .eq("document_id", document_id)
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