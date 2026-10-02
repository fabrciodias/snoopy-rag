from abc import ABC, abstractmethod
from typing import List, Optional

from backend.domain.entities import (
    Document,
    DocumentRepresentation,
    DocumentStatus,
    Evidence,
    Investigation,
    InvestigationStatus,
    Operation,
    OperationStatus,
    RetrievalResult,
    RetrievalUnit,
    StructuredResponse,
)


# ============================================================
# Operation Repository
# ============================================================

class OperationRepository(ABC):

    @abstractmethod
    def create(
        self,
        operation: Operation,
    ) -> Operation:
        pass

    @abstractmethod
    def get_by_id(
        self,
        operation_id: str,
    ) -> Optional[Operation]:
        pass

    @abstractmethod
    def update_status(
        self,
        operation_id: str,
        status: OperationStatus,
        error_log: Optional[str] = None,
    ) -> Operation:
        pass


# ============================================================
# Document Repository
# ============================================================

class DocumentRepository(ABC):

    @abstractmethod
    def create_or_update(
        self,
        document: Document,
    ) -> Document:
        """
        Cria ou atualiza a entidade documental.

        A identidade e os metadados persistentes do documento
        pertencem ao próprio contrato Document.
        """
        pass

    @abstractmethod
    def get_by_id(
        self,
        document_id: str,
    ) -> Optional[Document]:
        pass

    @abstractmethod
    def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> Document:
        pass

    @abstractmethod
    def save_representation(
        self,
        document_id: str,
        representation: DocumentRepresentation,
    ) -> Document:
        """
        Persiste uma nova representação histórica.

        Esta operação NÃO altera a representação corrente
        do documento e NÃO publica a nova versão.
        """
        pass

    @abstractmethod
    def publish_representation(
        self,
        document: Document,
        representation: DocumentRepresentation,
    ) -> Document:
        """
        Publica uma representação previamente processada.

        A representação passa a ser a versão corrente do documento
        somente depois que todo o pipeline de processamento tiver
        sido concluído com sucesso.
        """
        pass

    @abstractmethod
    def get_representation(
        self,
        document_id: str,
    ) -> Optional[DocumentRepresentation]:
        pass


# ============================================================
# Retrieval Unit Repository
# ============================================================

class RetrievalUnitRepository(ABC):

    @abstractmethod
    def save_batch(
        self,
        units: List[RetrievalUnit],
        embeddings: List[List[float]],
    ) -> List[RetrievalUnit]:
        """
        Persiste RetrievalUnits e seus vetores associados.

        user_id e folder_id não fazem parte da identidade da
        RetrievalUnit; são contexto de autorização/persistência
        derivado do documento e do acervo.
        """
        pass

    @abstractmethod
    def get_context(
        self,
        unit_id: int,
        window: int = 1,
    ) -> List[RetrievalUnit]:
        """
        Recupera a unidade indicada e suas unidades vizinhas
        dentro da mesma representação documental.

        A unidade recuperada continua sendo a evidência principal.
        As demais unidades são utilizadas apenas como contexto.
        """
        pass


# ============================================================
# Embedding Provider
# ============================================================

class EmbeddingProvider(ABC):

    @abstractmethod
    def generate_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        pass


# ============================================================
# Investigation Repository
# ============================================================

class InvestigationRepository(ABC):

    @abstractmethod
    def create(
        self,
        investigation: Investigation,
    ) -> Investigation:
        pass

    @abstractmethod
    def get_by_id(
        self,
        investigation_id: str,
    ) -> Optional[Investigation]:
        pass

    @abstractmethod
    def update_status(
        self,
        investigation_id: str,
        status: InvestigationStatus,
    ) -> Investigation:
        pass

    @abstractmethod
    def save_structured_response(
        self,
        investigation_id: str,
        response: StructuredResponse,
    ) -> Investigation:
        pass


# ============================================================
# Retrieval Result Repository
# ============================================================

class RetrievalResultRepository(ABC):

    @abstractmethod
    def save_batch(
        self,
        results: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        pass

    @abstractmethod
    def get_by_investigation(
        self,
        investigation_id: str,
    ) -> List[RetrievalResult]:
        pass


# ============================================================
# Evidence Repository
# ============================================================

class EvidenceRepository(ABC):

    @abstractmethod
    def save_batch(
        self,
        evidences: List[Evidence],
    ) -> List[Evidence]:
        pass

    @abstractmethod
    def get_by_investigation(
        self,
        investigation_id: str,
    ) -> List[Evidence]:
        pass

    @abstractmethod
    def get_by_id(
        self,
        evidence_id: str,
    ) -> Optional[Evidence]:
        pass