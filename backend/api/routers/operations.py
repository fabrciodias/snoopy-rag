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
    operation_service,
)


router = APIRouter(
    prefix="/operations",
    tags=["Operations"],
)


@router.get("/{operation_id}")
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
