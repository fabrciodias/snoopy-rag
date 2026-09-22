from abc import ABC, abstractmethod
from typing import Optional, List

from backend.domain.entities import (
    Operation,
    OperationStatus,
    DocumentStatus,
    RetrievalUnit,
    DocumentRepresentation,
    Investigation,
    RetrievalResult,
    Evidence,
)


class OperationRepository(ABC):

    @abstractmethod
    def create(self, operation: Operation) -> Operation:
        pass

    @abstractmethod
    def get_by_id(self, operation_id: str) -> Optional[Operation]:
        pass

    @abstractmethod
    def update_status(
        self,
        operation_id: str,
        status: OperationStatus,
        error_log: Optional[str] = None,
    ) -> Operation:
        pass


class DocumentRepository(ABC):

    @abstractmethod
    def create_or_update(
        self,
        document_id: str,
        title: str,
        folder_id: str,
        user_id: str,
        drive_file_id: str,
        document_hash: str,
    ) -> None:
        pass

    @abstractmethod
    def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> None:
        pass

    @abstractmethod
    def save_representation(
        self,
        document_id: str,
        representation: DocumentRepresentation,
    ) -> None:
        pass

    @abstractmethod
    def get_representation(
        self,
        document_id: str,
    ) -> Optional[DocumentRepresentation]:
        pass


class RetrievalUnitRepository(ABC):

    @abstractmethod
    def save_batch(
        self,
        units: List[RetrievalUnit],
        embeddings: List[List[float]],
        user_id: str,
        folder_id: str,
    ) -> List[RetrievalUnit]:
        pass

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None:
        pass


class EmbeddingProvider(ABC):

    @abstractmethod
    def generate_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        pass


class InvestigationRepository(ABC):

    @abstractmethod
    def create(self, investigation: Investigation) -> Investigation:
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
        status: str,
    ) -> Investigation:
        pass

    @abstractmethod
    def save_structured_response(
        self,
        investigation_id: str,
        response: dict,
    ) -> None:
        pass


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