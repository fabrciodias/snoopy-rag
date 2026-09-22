from typing import Optional, List

from supabase import Client

from backend.domain.entities import (
    Operation,
    OperationStatus,
    DocumentStatus,
    DocumentRepresentation,
    RetrievalUnit,
    Investigation,
    RetrievalResult,
    Evidence,
)

from backend.domain.repositories import (
    OperationRepository,
    DocumentRepository,
    RetrievalUnitRepository,
    InvestigationRepository,
    RetrievalResultRepository,
    EvidenceRepository,
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

        record = response.data[0]
        record["operation_id"] = record.pop("id")

        return Operation(**record)

    def get_by_id(
        self,
        operation_id: str,
    ) -> Optional[Operation]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("id", operation_id)
            .execute()
        )

        if not response.data:
            return None

        record = response.data[0]
        record["operation_id"] = record.pop("id")

        return Operation(**record)

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
            from datetime import datetime, timezone

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

        record = response.data[0]
        record["operation_id"] = record.pop("id")

        return Operation(**record)


# ============================================================
# Documents
# ============================================================

class SupabaseDocumentRepository(DocumentRepository):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "documents"

    def create_or_update(
        self,
        document_id: str,
        title: str,
        folder_id: str,
        user_id: str,
        drive_file_id: str,
        document_hash: str,
    ) -> None:

        payload = {
            "id": document_id,
            "title": title,
            "folder_id": folder_id,
            "user_id": user_id,
            "drive_file_id": drive_file_id,
            "document_hash": document_hash,
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

    def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> None:

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

    def save_representation(
        self,
        document_id: str,
        representation: DocumentRepresentation,
    ) -> None:

        response = (
            self.client
            .table(self.table_name)
            .update({
                "representation": representation.model_dump(
                    mode="json"
                ),
            })
            .eq("id", document_id)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Documento '{document_id}' não encontrado."
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
        user_id: str,
        folder_id: str,
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
                "folder_id": folder_id,
                "user_id": user_id,
                "content": unit.content,
                "section": unit.section,
                "embedding": embedding,
                "unit_index": unit.unit_index,
                "location": unit.location,
                "representation_id": unit.representation_id,
            })

        response = (
            self.client
            .table(self.table_name)
            .insert(payload)
            .execute()
        )

        if len(response.data) != len(units):
            raise RuntimeError(
                "Nem todas as RetrievalUnits foram persistidas."
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

        record = response.data[0]
        record["investigation_id"] = record.pop("id")

        return Investigation(**record)

    def get_by_id(
        self,
        investigation_id: str,
    ) -> Optional[Investigation]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("id", investigation_id)
            .execute()
        )

        if not response.data:
            return None

        record = response.data[0]
        record["investigation_id"] = record.pop("id")

        return Investigation(**record)

    def update_status(
        self,
        investigation_id: str,
        status: str,
    ) -> Investigation:

        response = (
            self.client
            .table(self.table_name)
            .update({"status": status})
            .eq("id", investigation_id)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Investigação '{investigation_id}' não encontrada."
            )

        record = response.data[0]
        record["investigation_id"] = record.pop("id")

        return Investigation(**record)

    def save_structured_response(
        self,
        investigation_id: str,
        response: dict,
    ) -> None:

        self.client \
            .table(self.table_name) \
            .update({
                "structured_response": response,
                "status": "COMPLETED",
            }) \
            .eq("id", investigation_id) \
            .execute()


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
                "investigation_id": result.investigation_id,
                "unit_id": result.unit_id,
                "rank": result.rank,
                "retrieval_score": result.retrieval_score,
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

        return results

    def get_by_investigation(
        self,
        investigation_id: str,
    ) -> List[RetrievalResult]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("investigation_id", investigation_id)
            .order("rank")
            .execute()
        )

        return [
            RetrievalResult(
                result_id=row["id"],
                investigation_id=row["investigation_id"],
                unit_id=row["unit_id"],
                rank=row["rank"],
                retrieval_score=row["retrieval_score"],
                metadata=row.get("metadata") or {},
            )
            for row in response.data
        ]


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
                "investigation_id": evidence.investigation_id,
                "unit_id": evidence.unit_id,
                "document_id": evidence.document_id,
                "location": evidence.location,
                "content": evidence.content,
                "context": evidence.context,
                "provenance": evidence.provenance,
            })

        response = (
            self.client
            .table(self.table_name)
            .insert(payload)
            .execute()
        )

        if len(response.data) != len(evidences):
            raise RuntimeError(
                "Nem todas as evidências foram persistidas."
            )

        return evidences

    def get_by_investigation(
        self,
        investigation_id: str,
    ) -> List[Evidence]:

        response = (
            self.client
            .table(self.table_name)
            .select("*")
            .eq("investigation_id", investigation_id)
            .order("created_at")
            .execute()
        )

        return [
            Evidence(
                evidence_id=row["id"],
                investigation_id=row["investigation_id"],
                unit_id=row["unit_id"],
                document_id=row["document_id"],
                location=row.get("location") or {},
                content=row["content"],
                context=row.get("context") or "",
                provenance=row.get("provenance") or {},
            )
            for row in response.data
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
            .execute()
        )

        if not response.data:
            return None

        row = response.data[0]

        return Evidence(
            evidence_id=row["id"],
            investigation_id=row["investigation_id"],
            unit_id=row["unit_id"],
            document_id=row["document_id"],
            location=row.get("location") or {},
            content=row["content"],
            context=row.get("context") or "",
            provenance=row.get("provenance") or {},
        )