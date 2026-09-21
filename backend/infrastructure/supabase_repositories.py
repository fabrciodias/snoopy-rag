from typing import Optional, List
from datetime import datetime, timezone
from supabase import Client
from backend.domain.entities import Operation, OperationStatus, DocumentStatus, RetrievalUnit
from backend.domain.repositories import OperationRepository, DocumentRepository, RetrievalUnitRepository

class SupabaseOperationRepository(OperationRepository):
    """
    Implementação concreta do repositório de Operações utilizando o Supabase.
    Isola o uso da biblioteca 'supabase-py' exclusivamente nesta camada.
    """

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "operations"

    def create(self, operation: Operation) -> Operation:
        data = operation.model_dump(exclude_none=True)
        
        if "started_at" in data and isinstance(data["started_at"], datetime):
            data["started_at"] = data["started_at"].isoformat()
            
        response = self.client.table(self.table_name).insert(data).execute()
        
        db_record = response.data[0]
        db_record["operation_id"] = db_record.pop("id")
        
        return Operation(**db_record)

    def get_by_id(self, operation_id: str) -> Optional[Operation]:
        response = self.client.table(self.table_name).select("*").eq("id", operation_id).execute()
        
        if not response.data:
            return None
            
        db_record = response.data[0]
        db_record["operation_id"] = db_record.pop("id")
        
        return Operation(**db_record)

    def update_status(self, operation_id: str, status: OperationStatus, error_log: Optional[str] = None) -> Operation:
        update_data = {"status": status.value}
        
        if error_log:
            update_data["error_log"] = error_log
            
        if status in (OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED):
            update_data["finished_at"] = datetime.now(timezone.utc).isoformat()
            
        response = self.client.table(self.table_name).update(update_data).eq("id", operation_id).execute()
        
        db_record = response.data[0]
        db_record["operation_id"] = db_record.pop("id")
        
        return Operation(**db_record)

class SupabaseDocumentRepository(DocumentRepository):
    def __init__(self, client: Client):
        self.client = client
        self.table_name = "documents"

    def create_or_update(self, document_id: str, title: str, folder_id: str, user_id: str, drive_file_id: str, document_hash: str) -> None:
        data = {
            "id": document_id,
            "title": title,
            "folder_id": folder_id,
            "user_id": user_id,
            "drive_file_id": drive_file_id,
            "document_hash": document_hash,
            "status": DocumentStatus.PROCESSING.value
        }
        self.client.table(self.table_name).upsert(data).execute()

    def update_status(self, document_id: str, status: DocumentStatus) -> None:
        self.client.table(self.table_name).update({"status": status.value}).eq("id", document_id).execute()

class SupabaseRetrievalUnitRepository(RetrievalUnitRepository):
    def __init__(self, client: Client):
        self.client = client
        self.table_name = "chunks"

    def save_batch(self, units: List[RetrievalUnit], embeddings: List[List[float]], user_id: str, folder_id: str) -> None:
        payload = []
        for unit, emb in zip(units, embeddings):
            payload.append({
                "document_id": unit.document_id,
                "folder_id": folder_id,
                "user_id": user_id,
                "content": unit.content,
                "section": unit.section,
                "unit_index": unit.unit_index,
                "location": unit.location,
                "embedding": emb
            })
        
        if payload:
            self.client.table(self.table_name).insert(payload).execute()

    