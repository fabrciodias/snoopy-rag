import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
)

from pydantic import BaseModel

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
    PUBLIC_FOLDER_ID,
)

from backend.api.container import (
    operation_service,
    drive_sync_service,
)

from backend.domain.entities import (
    OperationProgress,
    OperationTargetType,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sync-drive",
    tags=["Documents"],
)


class DriveSyncRequest(BaseModel):
    folder_id: str
    google_token: str


@router.post("/")
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
    if request.folder_id == PUBLIC_FOLDER_ID:
        raise HTTPException(
            status_code=403,
            detail=(
                "O acervo público não pode ser "
                "sincronizado pelo frontend."
            ),
        )

    if not folder.get("drive_id"):
        raise HTTPException(
            status_code=400,
            detail=(
                "O acervo não possui uma pasta do "
                "Google Drive vinculada."
            ),
        )

    try:
        # 1. Procura uma sincronização já ativa.
        # A consulta não modifica o estado da operação.
        operation = operation_service.get_active_operation(
            operation_type="DRIVE_SYNC",
            target_type=OperationTargetType.FOLDER,
            target_id=request.folder_id,
        )

        if operation is not None:
            return {
                "operation_id": operation.operation_id,
                "status": operation.status,
            }

        # 2. Não havendo operação ativa, cria uma nova
        # já com o progresso inicial persistível.
        try:
            operation = operation_service.start_operation(
                operation_type="DRIVE_SYNC",
                target_type=OperationTargetType.FOLDER,
                target_id=request.folder_id,
                progress=OperationProgress(
                    phase="starting",
                    message="Preparando sincronização...",
                    current=0,
                    unit="files",
                ),
            )

        except Exception:
            # Uma requisição concorrente pode ter criado
            # a operação entre a consulta e a inserção.
            existing_operation = (
                operation_service.get_active_operation(
                    operation_type="DRIVE_SYNC",
                    target_type=OperationTargetType.FOLDER,
                    target_id=request.folder_id,
                )
            )

            # Não ocultamos o erro original se não houver
            # uma operação ativa que explique a concorrência.
            if existing_operation is None:
                raise

            return {
                "operation_id": existing_operation.operation_id,
                "status": existing_operation.status,
            }

        if not operation.operation_id:
            raise RuntimeError(
                "A operação de sincronização não recebeu "
                "um identificador válido."
            )

        # 3. Somente a requisição que criou a operação
        # agenda o processamento em background.
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
        logger.exception(
            "Falha interna ao iniciar sincronização do Drive."
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível iniciar a sincronização. " \
                "Tente novamente."
            ),
        ) from error