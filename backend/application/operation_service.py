from typing import Optional
from datetime import datetime, timezone
from backend.domain.entities import Operation, OperationStatus
from backend.domain.repositories import OperationRepository

class OperationService:
    """
    Orquestrador de execuções assíncronas do Snoopy V3.
    Garante a regra arquitetural: O estado de uma Operação (Ex: PROCESSING, FAILED)
    nunca deve ser confundido com o estado da entidade final (Ex: Documento ACTIVE).
    """

    def __init__(self, operation_repo: OperationRepository):
        # A injeção de dependência acontece aqui. O serviço recebe um banco de dados
        # que respeita o contrato, mas não precisa saber que é o Supabase.
        self.operation_repo = operation_repo

    def start_operation(self, operation_type: str, target_id: Optional[str] = None) -> Operation:
        """Inicia uma nova operação, gerando uma identidade única para acompanhamento."""
        operation = Operation(
            operation_type=operation_type,
            target_id=target_id,
            status=OperationStatus.PROCESSING,
            started_at=datetime.now(timezone.utc)
        )
        return self.operation_repo.create(operation)

    def complete_operation(self, operation_id: str) -> Operation:
        """Crava o sucesso da execução na linha do tempo."""
        return self.operation_repo.update_status(operation_id, OperationStatus.COMPLETED)

    def fail_operation(self, operation_id: str, error_msg: str) -> Operation:
        """
        Registra a falha detalhada. O erro fica isolado na Operação, 
        permitindo diagnóstico sem corromper o estado lógico do documento.
        """
        return self.operation_repo.update_status(operation_id, OperationStatus.FAILED, error_log=error_msg)

    def get_operation_state(self, operation_id: str) -> Optional[Operation]:
        """
        Consulta o estado autoritativo. Substitui a necessidade de "adivinhar"
        se um processo terminou caso a conexão SSE (tempo real) caia.
        """
        return self.operation_repo.get_by_id(operation_id)