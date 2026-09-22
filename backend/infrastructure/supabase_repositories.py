from typing import Optional, List
from datetime import datetime, timezone

from supabase import Client

from backend.domain.entities import (
    Operation,
    OperationStatus,
    DocumentStatus,
    DocumentRepresentation,
    RetrievalUnit,
)
from backend.domain.repositories import (
    OperationRepository,
    DocumentRepository,
    RetrievalUnitRepository,
)


class SupabaseOperationRepository(OperationRepository):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "operations"

    def create(self, operation: Operation) -> Operation:
        data = operation.model_dump(mode="json", exclude_none=True)

        response = self.client \
            .table(self.table_name) \
            .insert(data) \
            .execute()

        db_record = response.data[0]

        db_record["operation_id"] = db_record.pop("id")

        return Operation(**db_record)

    def get_by_id(self, operation_id: str) -> Optional[Operation]:
        response = self.client \
            .table(self.table_name) \
            .select("*") \
            .eq("id", operation_id) \
            .execute()

        if not response.data:
            return None

        db_record = response.data[0]
        db_record["operation_id"] = db_record.pop("id")

        return Operation(**db_record)

    def update_status(
        self,
        operation_id: str,
        status: OperationStatus,
        error_log: Optional[str] = None,
    ) -> Operation:

        update_data = {
            "status": status.value,
        }

        if error_log is not None:
            update_data["error_log"] = error_log

        if status == OperationStatus.PROCESSING:
            update_data["started_at"] = datetime.now(timezone.utc).isoformat()

        if status in (
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        ):
            update_data["finished_at"] = datetime.now(timezone.utc).isoformat()

        response = self.client \
            .table(self.table_name) \
            .update(update_data) \
            .eq("id", operation_id) \
            .execute()

        if not response.data:
            raise RuntimeError(
                f"Operação '{operation_id}' não encontrada."
            )

        db_record = response.data[0]
        db_record["operation_id"] = db_record.pop("id")

        return Operation(**db_record)


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

        data = {
            "id": document_id,
            "title": title,
            "folder_id": folder_id,
            "user_id": user_id,
            "drive_file_id": drive_file_id,
            "document_hash": document_hash,
            "status": DocumentStatus.PENDING.value,
        }

        self.client \
            .table(self.table_name) \
            .upsert(data) \
            .execute()

    def save_representation(
        self,
        document_id: str,
        representation: DocumentRepresentation,
    ) -> None:

        data = {
            "representation": representation.model_dump(
                mode="json",
                exclude_none=True,
            )
        }

        self.client \
            .table(self.table_name) \
            .update(data) \
            .eq("id", document_id) \
            .execute()

    def get_representation(
        self,
        document_id: str,
    ) -> Optional[DocumentRepresentation]:

        response = self.client \
            .table(self.table_name) \
            .select("representation") \
            .eq("id", document_id) \
            .execute()

        if not response.data:
            return None

        raw = response.data[0].get("representation")

        if not raw:
            return None

        return DocumentRepresentation(**raw)

    def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> None:

        self.client \
            .table(self.table_name) \
            .update({"status": status.value}) \
            .eq("id", document_id) \
            .execute()


class SupabaseRetrievalUnitRepository(RetrievalUnitRepository):

    """
    Adapter físico:
        RetrievalUnit → chunks

    'chunks' é apenas a persistência legada utilizada pela Alpha.
    O domínio não conhece esse nome.
    """

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

        if len(units) != len(embeddings):
            raise ValueError(
                "Quantidade de RetrievalUnits e embeddings deve ser igual."
            )

        payload = []

        for unit, embedding in zip(units, embeddings):
            payload.append({
                "document_id": unit.document_id,
                "representation_id": unit.representation_id,
                "folder_id": folder_id,
                "user_id": user_id,
                "content": unit.content,
                "section": unit.section,
                "unit_index": unit.unit_index,
                "location": unit.location,
                "embedding": embedding,
            })

        if not payload:
            return []

        response = self.client \
            .table(self.table_name) \
            .insert(payload) \
            .execute()

        created_units = []

        for unit, db_record in zip(units, response.data):
            created_units.append(
                unit.model_copy(
                    update={
                        "unit_id": db_record["id"],
                    }
                )
            )

        return created_units

    def delete_by_document(self, document_id: str) -> None:
        self.client \
            .table(self.table_name) \
            .delete() \
            .eq("document_id", document_id) \
            .execute()