from datetime import datetime, timezone
from typing import Optional

from backend.domain.entities import (
    Operation,
    OperationStatus,
    OperationTargetType,
)
from backend.domain.repositories import OperationRepository


class OperationService:
    """
    Orquestrador de execuções assíncronas do Snoopy V3.

    O estado da operação descreve a execução do processo.
    O estado da entidade alvo continua pertencendo à própria
    entidade.
    """

    def __init__(
        self,
        operation_repo: OperationRepository,
    ):
        self.operation_repo = operation_repo

    def start_operation(
        self,
        operation_type: str,
        target_type: Optional[OperationTargetType] = None,
        target_id: Optional[str] = None,
    ) -> Operation:

        operation = Operation(
            operation_type=operation_type,
            target_type=target_type,
            target_id=target_id,
            status=OperationStatus.PROCESSING,
            started_at=datetime.now(timezone.utc),
        )

        return self.operation_repo.create(operation)

    def complete_operation(
        self,
        operation_id: str,
    ) -> Operation:

        return self.operation_repo.update_status(
            operation_id,
            OperationStatus.COMPLETED,
        )

    def fail_operation(
        self,
        operation_id: str,
        error_msg: str,
    ) -> Operation:

        return self.operation_repo.update_status(
            operation_id,
            OperationStatus.FAILED,
            error_log=error_msg,
        )

    def get_operation_state(
        self,
        operation_id: str,
    ) -> Optional[Operation]:

        return self.operation_repo.get_by_id(
            operation_id
        )
