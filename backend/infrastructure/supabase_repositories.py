from datetime import datetime, timezone
from typing import List, Optional

from supabase import Client

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

from backend.domain.repositories import (
    DocumentRepository,
    EvidenceRepository,
    InvestigationRepository,
    OperationRepository,
    RetrievalResultRepository,
    RetrievalUnitRepository,
)


# ============================================================
# Operations
# ============================================================


class SupabaseOperationRepository(OperationRepository):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "operations"

    def create(
        self,
        operation: Operation,
    ) -> Operation:

        data = operation.model_dump(
            mode="json",
            exclude_none=True,
        )

        if "operation_id" in data:
            data["id"] = data.pop("operation_id")

        response = (
            self.client
            .table(self.table_name)
            .insert(data)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Falha ao persistir a operação."
            )

        return self._to_entity(response.data[0])

    def get_by_id(
        self,
        operation_id: str,
    ) -> Optional[Operation]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("id", operation_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._to_entity(response.data[0])

    def update_status(
        self,
        operation_id: str,
        status: OperationStatus,
        error_log: Optional[str] = None,
    ) -> Operation:

        payload = {
            "status": status.value,
            "error_log": error_log,
        }

        if status in (
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        ):
            payload["finished_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

        response = (
            self.client
            .table(self.table_name)
            .update(payload)
            .eq("id", operation_id)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Operação '{operation_id}' não encontrada."
            )

        return self._to_entity(response.data[0])

    @staticmethod
    def _to_entity(
        record: dict,
    ) -> Operation:

        data = dict(record)

        data["operation_id"] = data.pop("id")

        return Operation(**data)


# ============================================================
# Documents
# ============================================================


class SupabaseDocumentRepository(DocumentRepository):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "documents"

    def create_or_update(
        self,
        document: Document,
    ) -> Document:

        payload = {
            "id": document.document_id,
            "folder_id": document.folder_id,
            "user_id": document.user_id,
            "title": document.title,
            "authors": document.authors,
            "publication_year": document.publication_year,
            "drive_file_id": document.drive_file_id,
            "drive_link": document.drive_link,
            "document_hash": document.document_hash,
            "status": document.status.value,
        }

        response = (
            self.client
            .table(self.table_name)
            .upsert(
                payload,
                on_conflict="id",
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Falha ao criar ou atualizar o documento."
            )

        return self._to_entity(response.data[0])

    def get_by_id(
        self,
        document_id: str,
    ) -> Optional[Document]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._to_entity(response.data[0])

    def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> Document:

        response = (
            self.client
            .table(self.table_name)
            .update({
                "status": status.value,
            })
            .eq("id", document_id)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Documento '{document_id}' não encontrado."
            )

        return self._to_entity(response.data[0])

    def save_representation(
        self,
        document_id: str,
        representation: DocumentRepresentation,
    ) -> Document:

        representation_payload = {
            "id": representation.representation_id,
            "document_id": document_id,
            "representation": representation.model_dump(
            mode="json"
            ),
        }

        history_response = (
            self.client
            .table("document_representations")
            .insert(representation_payload)
            .execute()
        )

        if not history_response.data:
            raise RuntimeError(
                "Falha ao persistir a representação documental."
            )

        document_response = (
            self.client
            .table(self.table_name)
            .update({
                "current_representation_id": (
                    representation.representation_id
                ),
                "representation": (
                    representation.model_dump(
                        mode="json"
                    )
                ),
            })
            .eq("id", document_id)
            .execute()
        )

        if not document_response.data:
            raise RuntimeError(
                f"Documento '{document_id}' não encontrado."
            )

        return self._to_entity(
            document_response.data[0]
        )


    def get_representation(
        self,
        document_id: str,
    ) -> Optional[DocumentRepresentation]:

        response = (
            self.client
            .table(self.table_name)
            .select("representation")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        representation = response.data[0].get(
            "representation"
        )

        if not representation:
            return None

        return DocumentRepresentation(**representation)

    @staticmethod
    def _to_entity(
        record: dict,
    ) -> Document:

        data = dict(record)

        representation = data.pop(
            "representation",
            None,
        )

        data["document_id"] = data.pop("id")

        if representation:
            data["representation"] = (
                DocumentRepresentation(**representation)
            )

        return Document(**data)


# ============================================================
# Retrieval Units
# ============================================================


class SupabaseRetrievalUnitRepository(
    RetrievalUnitRepository
):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "chunks"

    def save_batch(
        self,
        units: List[RetrievalUnit],
        embeddings: List[List[float]],
    ) -> List[RetrievalUnit]:

        if not units:
            return []

        if len(units) != len(embeddings):
            raise ValueError(
                "Quantidade de embeddings não corresponde "
                "às RetrievalUnits."
            )

        payload = []

        for unit, embedding in zip(
            units,
            embeddings,
        ):
            payload.append({
                "document_id": unit.document_id,
                "content": unit.content,
                "section": unit.section,
                "embedding": embedding,
                "unit_index": unit.unit_index,
                "location": unit.location.model_dump(
                    mode="json"
                ),
                "representation_id": (
                    unit.representation_id
                ),
            })

        response = (
            self.client
            .table(self.table_name)
            .insert(payload)
            .execute()
        )

        if len(response.data) != len(units):
            raise RuntimeError(
                "Nem todas as RetrievalUnits "
                "foram persistidas."
            )

        for unit, record in zip(
            units,
            response.data,
        ):
            unit.unit_id = record["id"]

        return units

    def delete_by_document(
        self,
        document_id: str,
    ) -> None:

        (
            self.client
            .table(self.table_name)
            .delete()
            .eq("document_id", document_id)
            .execute()
        )

    def get_context(
        self,
        unit_id: int,
        window: int = 1,
    ) -> List[RetrievalUnit]:

        if window < 0:
            raise ValueError(
                "A janela de contexto não pode ser negativa."
            )

        anchor_response = (
            self.client
            .table(self.table_name)
            .select(
                "id, document_id, representation_id, "
                "unit_index"
            )
            .eq("id", unit_id)
            .limit(1)
            .execute()
        )

        if not anchor_response.data:
            return []

        anchor = anchor_response.data[0]

        document_id = anchor["document_id"]
        representation_id = anchor["representation_id"]
        anchor_index = anchor["unit_index"]

        response = (
            self.client
            .table(self.table_name)
            .select(
                "id, document_id, representation_id, "
                "unit_index, content, location, section"
            )
            .eq(
                "document_id",
                document_id,
            )
            .eq(
                "representation_id",
                representation_id,
            )
            .gte(
                "unit_index",
                max(0, anchor_index - window),
            )
            .lte(
                "unit_index",
                anchor_index + window,
            )
            .order("unit_index")
            .execute()
        )

        results = []

        for record in response.data:
            results.append(
                RetrievalUnit(
                    unit_id=record["id"],
                    document_id=record["document_id"],
                    representation_id=(
                        record["representation_id"]
                    ),
                    unit_index=record["unit_index"],
                    content=record["content"],
                    location=(
                        record.get("location") or {}
                    ),
                    section=(
                        record.get("section")
                        or "Geral"
                    ),
                )
            )

        return results


# ============================================================
# Investigations
# ============================================================


class SupabaseInvestigationRepository(
    InvestigationRepository
):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "investigations"

    def create(
        self,
        investigation: Investigation,
    ) -> Investigation:

        data = investigation.model_dump(
            mode="json",
            exclude_none=True,
        )

        if "investigation_id" in data:
            data["id"] = data.pop("investigation_id")

        response = (
            self.client
            .table(self.table_name)
            .insert(data)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Falha ao persistir a investigação."
            )

        return self._to_entity(response.data[0])

    def get_by_id(
        self,
        investigation_id: str,
    ) -> Optional[Investigation]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("id", investigation_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._to_entity(response.data[0])

    def update_status(
        self,
        investigation_id: str,
        status: InvestigationStatus,
    ) -> Investigation:

        response = (
            self.client
            .table(self.table_name)
            .update({
                "status": status.value,
            })
            .eq("id", investigation_id)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Investigação '{investigation_id}' "
                "não encontrada."
            )

        return self._to_entity(response.data[0])

    def save_structured_response(
        self,
        investigation_id: str,
        response: StructuredResponse,
    ) -> Investigation:

        payload = {
            "structured_response": response.model_dump(
                mode="json"
            ),
            "status": InvestigationStatus.COMPLETED.value,
        }

        result = (
            self.client
            .table(self.table_name)
            .update(payload)
            .eq("id", investigation_id)
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                f"Investigação '{investigation_id}' "
                "não encontrada."
            )

        return self._to_entity(result.data[0])

    @staticmethod
    def _to_entity(
        record: dict,
    ) -> Investigation:

        data = dict(record)

        data["investigation_id"] = data.pop("id")

        structured_response = data.get(
            "structured_response"
        )

        if structured_response:
            data["structured_response"] = (
                structured_response
            )

        return Investigation(**data)


# ============================================================
# Retrieval Results
# ============================================================


class SupabaseRetrievalResultRepository(
    RetrievalResultRepository
):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "retrieval_results"

    def save_batch(
        self,
        results: List[RetrievalResult],
    ) -> List[RetrievalResult]:

        if not results:
            return []

        payload = []

        for result in results:
            payload.append({
                "id": result.result_id,
                "investigation_id": (
                    result.investigation_id
                ),
                "unit_id": result.unit_id,
                "document_id": result.document_id,
                "representation_id": result.representation_id,
                "rank": result.rank,
                "retrieval_score": (
                    result.retrieval_score
                ),
                "semantic_score": (
                    result.semantic_score
                ),
                "lexical_score": (
                    result.lexical_score
                ),
                "content": result.content,
                "location": result.location.model_dump(
                    mode="json"
                ),
                "metadata": result.metadata,
            })

        response = (
            self.client
            .table(self.table_name)
            .insert(payload)
            .execute()
        )

        if len(response.data) != len(results):
            raise RuntimeError(
                "Nem todos os RetrievalResults "
                "foram persistidos."
            )

        return [
            self._to_entity(record)
            for record in response.data
        ]

    def get_by_investigation(
        self,
        investigation_id: str,
    ) -> List[RetrievalResult]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq(
                "investigation_id",
                investigation_id,
            )
            .order("rank")
            .execute()
        )

        return [
            self._to_entity(record)
            for record in response.data
        ]

    @staticmethod
    def _to_entity(
        record: dict,
    ) -> RetrievalResult:

        data = dict(record)

        data["result_id"] = data.pop("id")

        data["location"] = (
            data.get("location") or {}
        )

        data["metadata"] = (
            data.get("metadata") or {}
        )

        return RetrievalResult(**data)


# ============================================================
# Evidences
# ============================================================


class SupabaseEvidenceRepository(
    EvidenceRepository
):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "evidences"

    def save_batch(
        self,
        evidences: List[Evidence],
    ) -> List[Evidence]:

        if not evidences:
            return []

        payload = []

        for evidence in evidences:
            payload.append({
                "id": evidence.evidence_id,
                "investigation_id": (
                    evidence.investigation_id
                ),
                "unit_id": evidence.unit_id,
                "document_id": evidence.document_id,
                "location": evidence.location.model_dump(
                    mode="json"
                ),
                "content": evidence.content,
                "context": evidence.context,
                "provenance": (
                    evidence.provenance.model_dump(
                        mode="json"
                    )
                ),
            })

        response = (
            self.client
            .table(self.table_name)
            .insert(payload)
            .execute()
        )

        if len(response.data) != len(evidences):
            raise RuntimeError(
                "Nem todas as evidências "
                "foram persistidas."
            )

        return [
            self._to_entity(record)
            for record in response.data
        ]

    def get_by_investigation(
        self,
        investigation_id: str,
    ) -> List[Evidence]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq(
                "investigation_id",
                investigation_id,
            )
            .order("created_at")
            .execute()
        )

        return [
            self._to_entity(record)
            for record in response.data
        ]

    def get_by_id(
        self,
        evidence_id: str,
    ) -> Optional[Evidence]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("id", evidence_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._to_entity(
            response.data[0]
        )

    @staticmethod
    def _to_entity(
        record: dict,
    ) -> Evidence:

        data = dict(record)

        data["evidence_id"] = data.pop("id")

        data["location"] = (
            data.get("location") or {}
        )

        data["provenance"] = (
            data.get("provenance") or {}
        )

        return Evidence(**data)
