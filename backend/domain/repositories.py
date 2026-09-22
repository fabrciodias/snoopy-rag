from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from backend.domain.entities import Operation, OperationStatus, DocumentStatus, RetrievalUnit, DocumentRepresentation

class OperationRepository(ABC):
    """
    Contrato rigoroso para o repositório de Operações. 
    """
    @abstractmethod
    def create(self, operation: Operation) -> Operation:
        pass

    @abstractmethod
    def get_by_id(self, operation_id: str) -> Optional[Operation]:
        pass

    @abstractmethod
    def update_status(self, operation_id: str, status: OperationStatus, error_log: Optional[str] = None) -> Operation:
        pass


class DocumentRepository(ABC):
    @abstractmethod
    def create_or_update(self, document_id: str, title: str, folder_id: str, user_id: str, drive_file_id: str, document_hash: str) -> None:
        pass

    @abstractmethod
    def update_status(self, document_id: str, status: DocumentStatus) -> None:
        pass

    # NOVO: Obriga a persistência da representação documental canónica
    @abstractmethod
    def save_representation(self, document_id: str, representation: DocumentRepresentation) -> None:
        pass

    # NOVO: Permite reconstruir a localização e rastreabilidade a partir da representação preservada
    @abstractmethod
    def get_representation(self, document_id: str) -> Optional[DocumentRepresentation]:
        pass

class RetrievalUnitRepository(ABC):
    # ATUALIZADO: Fica explícito que a representação está atrelada à unidade na base de dados
    @abstractmethod
    def save_batch(self, units: List[RetrievalUnit], embeddings: List[List[float]], user_id: str, folder_id: str) -> None:
        pass

class EmbeddingProvider(ABC):
    """
    Contrato para geração de vetores semânticos (Embeddings).
    """
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass