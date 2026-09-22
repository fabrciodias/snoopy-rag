from typing import Optional, List

from supabase import Client

from backend.domain.entities import (
    Investigation,
    RetrievalResult,
    Evidence,
)

from backend.domain.repositories import (
    InvestigationRepository,
    RetrievalResultRepository,
    EvidenceRepository,
)


class SupabaseInvestigationRepository(InvestigationRepository):

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "investigations"

    def create(self, investigation: Investigation) -> Investigation:
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
                "Nem todos os RetrievalResults foram persistidos."
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


class SupabaseEvidenceRepository(EvidenceRepository):

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