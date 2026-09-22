import uuid
from typing import List
from datetime import datetime, timezone

from supabase import Client

from backend.domain.entities import (
    Investigation,
    RetrievalResult,
)
from backend.domain.repositories import (
    EmbeddingProvider,
    InvestigationRepository,
    RetrievalResultRepository,
)


class RetrievalService:

    def __init__(
        self,
        emb_provider: EmbeddingProvider,
        supabase_client: Client,
        investigation_repo: InvestigationRepository,
        result_repo: RetrievalResultRepository,
    ):
        self.emb_provider = emb_provider
        self.client = supabase_client
        self.investigation_repo = investigation_repo
        self.result_repo = result_repo

    def search(
        self,
        user_id: str,
        folder_id: str,
        query: str,
        limit: int = 10,
    ) -> tuple[Investigation, List[RetrievalResult]]:

        filters = {
            "folder_id": folder_id,
        }

        investigation = Investigation(
            investigation_id=str(uuid.uuid4()),
            user_id=user_id,
            original_query=query,
            filters=filters,
            status="PROCESSING",
            created_at=datetime.now(timezone.utc),
        )

        investigation = self.investigation_repo.create(
            investigation
        )

        try:
            query_embeddings = (
                self.emb_provider.generate_embeddings([query])
            )

            if not query_embeddings:
                self.investigation_repo.update_status(
                    investigation.investigation_id,
                    "COMPLETED",
                )
                return investigation, []

            vector = query_embeddings[0]

            response = self.client.rpc(
                "v3_hybrid_search",
                {
                    "p_query_text": query,
                    "p_query_embedding": vector,
                    "p_match_count": limit * 2,
                    "p_user_id": user_id,
                    "p_folder_id": folder_id,
                },
            ).execute()

            raw_results = response.data or []

            semantic_sorted = sorted(
                raw_results,
                key=lambda x: x.get("semantic_score", 0),
                reverse=True,
            )

            lexical_sorted = sorted(
                raw_results,
                key=lambda x: x.get("lexical_score", 0),
                reverse=True,
            )

            ranks = {}

            for rank, item in enumerate(semantic_sorted):
                ranks.setdefault(
                    item["unit_id"], {}
                )["semantic_rank"] = rank + 1

            for rank, item in enumerate(lexical_sorted):
                ranks.setdefault(
                    item["unit_id"], {}
                )["lexical_rank"] = rank + 1

            k = 60
            fused_results = []

            for item in raw_results:

                unit_id = item["unit_id"]

                semantic_rank = ranks[unit_id].get(
                    "semantic_rank",
                    1000,
                )

                lexical_rank = ranks[unit_id].get(
                    "lexical_rank",
                    1000,
                )

                rrf_score = (
                    1.0 / (k + semantic_rank)
                ) + (
                    1.0 / (k + lexical_rank)
                )

                item["rrf_score"] = rrf_score
                fused_results.append(item)

            fused_results = sorted(
                fused_results,
                key=lambda x: x["rrf_score"],
                reverse=True,
            )[:limit]

            results = []

            for idx, row in enumerate(fused_results):

                result = RetrievalResult(
                    result_id=str(uuid.uuid4()),
                    investigation_id=investigation.investigation_id,
                    unit_id=row["unit_id"],
                    rank=idx + 1,
                    retrieval_score=row["rrf_score"],
                    metadata={
                        "document_id": row["document_id"],
                        "content": row["content"],
                        "location": row["location"],
                        "raw_semantic_score": row.get(
                            "semantic_score",
                            0,
                        ),
                        "raw_lexical_score": row.get(
                            "lexical_score",
                            0,
                        ),
                    },
                )

                results.append(result)

            self.result_repo.save_batch(results)

            self.investigation_repo.update_status(
                investigation.investigation_id,
                "COMPLETED",
            )

            investigation.status = "COMPLETED"

            return investigation, results

        except Exception:
            self.investigation_repo.update_status(
                investigation.investigation_id,
                "FAILED",
            )
            raise