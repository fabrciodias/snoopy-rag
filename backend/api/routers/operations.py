import asyncio
import json
import time

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from sse_starlette.sse import EventSourceResponse

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
)

from backend.api.container import (
    operation_service,
    doc_repo,
    investigation_repo,
)

from backend.domain.entities import (
    OperationStatus,
    OperationTargetType,
)


router = APIRouter(
    prefix="/operations",
    tags=["Operations"],
)


def _ensure_target_access(
    target_type: OperationTargetType,
    target_id: str,
    user_id: str,
) -> None:
    """
    Autoriza o acesso ao alvo da operação.

    A autorização é determinada pelo tipo da entidade
    associada à operação, não apenas pelo seu identificador.

    O acervo continua sendo a fronteira de autorização
    para documentos e investigações.
    """

    if target_type == OperationTargetType.FOLDER:
        ensure_folder_access(
            target_id,
            user_id,
        )
        return

    if target_type == OperationTargetType.DOCUMENT:
        document = doc_repo.get_by_id(
            target_id
        )

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Operação não encontrada.",
            )

        try:
            ensure_folder_access(
                document.folder_id,
                user_id,
            )

        except HTTPException as error:
            if error.status_code in (403, 404):
                raise HTTPException(
                    status_code=404,
                    detail="Operação não encontrada.",
                ) from None

            raise

        return

    if target_type == OperationTargetType.INVESTIGATION:
        investigation = (
            investigation_repo.get_by_id(
                target_id
            )
        )

        if (
            investigation is None
            or investigation.user_id != user_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Operação não encontrada.",
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
                    detail="Operação não encontrada.",
                ) from None

            raise

        return

    raise HTTPException(
        status_code=500,
        detail="A operação possui um tipo de alvo inválido.",
    )


def _authorize_operation(
    operation,
    user_id: str,
) -> None:
    """
    Valida a entidade de destino e autoriza o acesso
    à operação.
    """

    if not operation.target_id:
        raise HTTPException(
            status_code=500,
            detail="Operação sem entidade de destino associada.",
        )

    if not operation.target_type:
        raise HTTPException(
            status_code=500,
            detail="Operação sem tipo de alvo válido.",
        )

    _ensure_target_access(
        operation.target_type,
        operation.target_id,
        user_id,
    )


def _sanitize_operation_error(
    operation,
):
    """
    Impede que detalhes internos da execução sejam
    expostos diretamente pela API.

    O erro técnico completo continua persistido no
    backend para diagnóstico.
    """

    safe_error = None

    if (
        operation.error_log
        and operation.status in (
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        )
    ):
        safe_error = (
            "A operação não foi concluída com sucesso. "
            "Os detalhes técnicos não são disponibilizados "
            "nesta resposta."
        )

    return operation.model_copy(
        update={
            "error_log": safe_error,
        }
    )


def _is_terminal_status(
    status: OperationStatus,
) -> bool:
    return status in (
        OperationStatus.COMPLETED,
        OperationStatus.FAILED,
        OperationStatus.CANCELLED,
    )


@router.get("/active")
def get_active_folder_sync(
    folder_id: str,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Recupera a sincronização ativa de um acervo.

    O usuário precisa continuar autorizado a acessar o acervo.
    A API é a fonte autoritativa do estado da operação.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    ensure_folder_access(
        folder_id,
        user_id,
    )

    operation = operation_service.get_active_operation(
        operation_type="DRIVE_SYNC",
        target_type=OperationTargetType.FOLDER,
        target_id=folder_id,
    )

    if operation is None:
        return None

    return _sanitize_operation_error(
        operation
    )


@router.get("/{operation_id}/events")
def stream_operation_events(
    operation_id: str,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Emite notificações SSE quando o estado persistido
    de uma operação muda.

    Os eventos identificam a operação, mas não constituem
    a fonte definitiva do seu estado.

    O frontend deve consultar GET /operations/{operation_id}
    após receber operation_changed.

    A conexão pode ser encerrada sem que a operação tenha
    sido cancelada. O cliente continua responsável por
    recuperar o estado por meio da API autoritativa.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    operation = operation_service.get_operation_state(
        operation_id
    )

    if operation is None:
        raise HTTPException(
            status_code=404,
            detail="Operação não encontrada.",
        )

    _authorize_operation(
        operation,
        user_id,
    )

    async def event_generator():
        previous_signature = None
        last_heartbeat = time.monotonic()

        while True:
            try:
                # As chamadas ao repositório são síncronas.
                # Não bloqueamos o event loop do servidor.
                current_operation = await asyncio.to_thread(
                    operation_service.get_operation_state,
                    operation_id,
                )

            except Exception:
                # A notificação apenas solicita uma nova
                # consulta à API. Nenhum detalhe técnico
                # interno é enviado ao cliente.
                yield {
                    "event": "operation_changed",
                    "data": json.dumps({
                        "operation_id": operation_id,
                    }),
                }

                await asyncio.sleep(1.5)
                continue

            if current_operation is None:
                yield {
                    "event": "operation_changed",
                    "data": json.dumps({
                        "operation_id": operation_id,
                    }),
                }

                return

            # O snapshot serve apenas para detectar mudanças.
            # Seu conteúdo não é enviado como estado autoritativo.
            signature = json.dumps(
                current_operation.model_dump(
                    mode="json",
                ),
                sort_keys=True,
                ensure_ascii=False,
            )

            if signature != previous_signature:
                previous_signature = signature
                last_heartbeat = time.monotonic()

                yield {
                    "event": "operation_changed",
                    "data": json.dumps({
                        "operation_id": operation_id,
                    }),
                }

            if _is_terminal_status(
                current_operation.status,
            ):
                return

            now = time.monotonic()

            if now - last_heartbeat >= 10:
                last_heartbeat = now

                # Heartbeat: mantém o cliente informado de
                # que o fluxo continua ativo. Não representa
                # uma mudança no estado da operação.
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "operation_id": operation_id,
                    }),
                }

            await asyncio.sleep(1.5)

    return EventSourceResponse(
        event_generator(),
        ping=15,
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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

    O acesso é autorizado a partir da entidade associada
    à operação e do acesso atual do usuário a essa entidade.

    O endpoint pode ser utilizado para polling e
    revalidação após perda de comunicação.
    """

    user_id = get_authenticated_user_id(
        authorization
    )

    operation = operation_service.get_operation_state(
        operation_id
    )

    if operation is None:
        raise HTTPException(
            status_code=404,
            detail="Operação não encontrada.",
        )

    _authorize_operation(
        operation,
        user_id,
    )

    return _sanitize_operation_error(
        operation
    )