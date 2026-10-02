import uuid
from datetime import datetime, timezone
from typing import List

from supabase import Client

from backend.domain.entities import (
    Investigation,
    InvestigationStatus,
    RetrievalResult,
)
from backend.domain.repositories import (
    EmbeddingProvider,
    InvestigationRepository,
    RetrievalResultRepository,
)


class RetrievalService:
    """
    Executa a recuperação híbrida de unidades documentais.

    Responsabilidades:
        1. Criar a Investigation.
        2. Gerar o embedding da consulta.
        3. Executar a recuperação híbrida no Supabase.
        4. Calcular os rankings individuais das modalidades.
        5. Combinar os rankings por Reciprocal Rank Fusion (RRF).
        6. Materializar e persistir RetrievalResults.
        7. Atualizar o estado da Investigation.
    """

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

        investigation = Investigation(
            investigation_id=str(uuid.uuid4()),
            user_id=user_id,
            folder_id=folder_id,
            original_query=query,
            status=InvestigationStatus.PROCESSING,
            created_at=datetime.now(timezone.utc),
        )

        investigation = self.investigation_repo.create(
            investigation
        )

        try:
            query_embeddings = (
                self.emb_provider.generate_embeddings(
                    [query]
                )
            )

            if not query_embeddings:
                investigation = (
                    self.investigation_repo.update_status(
                        investigation.investigation_id,
                        InvestigationStatus.COMPLETED,
                    )
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

            # ====================================================
            # 1. RANKING SEMÂNTICO
            # ====================================================

            semantic_sorted = sorted(
                (
                    item
                    for item in raw_results
                    if item.get("semantic_score")
                    is not None
                ),
                key=lambda item: item["semantic_score"],
                reverse=True,
            )

            # ====================================================
            # 2. RANKING LEXICAL
            # ====================================================

            lexical_sorted = sorted(
                (
                    item
                    for item in raw_results
                    if item.get("lexical_score")
                    is not None
                ),
                key=lambda item: item["lexical_score"],
                reverse=True,
            )

            # ====================================================
            # 3. RANKS POR MODALIDADE
            # ====================================================

            ranks = {}

            for rank, item in enumerate(
                semantic_sorted,
                start=1,
            ):
                ranks.setdefault(
                    item["unit_id"],
                    {},
                )["semantic_rank"] = rank

            for rank, item in enumerate(
                lexical_sorted,
                start=1,
            ):
                ranks.setdefault(
                    item["unit_id"],
                    {},
                )["lexical_rank"] = rank

            # ====================================================
            # 4. RECIPROCAL RANK FUSION
            # ====================================================

            k = 60
            fused_results = []

            for item in raw_results:

                unit_id = item["unit_id"]
                item_ranks = ranks[unit_id]

                semantic_rank = item_ranks.get(
                    "semantic_rank"
                )

                lexical_rank = item_ranks.get(
                    "lexical_rank"
                )

                rrf_score = 0.0

                if semantic_rank is not None:
                    rrf_score += 1.0 / (
                        k + semantic_rank
                    )

                if lexical_rank is not None:
                    rrf_score += 1.0 / (
                        k + lexical_rank
                    )

                item["rrf_score"] = rrf_score

                fused_results.append(item)

            fused_results = sorted(
                fused_results,
                key=lambda item: item["rrf_score"],
                reverse=True,
            )[:limit]

            # ====================================================
            # 5. MATERIALIZAÇÃO DOS RETRIEVAL RESULTS
            # ====================================================

            results = []

            for idx, row in enumerate(
                fused_results,
                start=1,
            ):
                result = RetrievalResult(
                    result_id=str(uuid.uuid4()),
                    investigation_id=(
                        investigation.investigation_id
                    ),
                    unit_id=row["unit_id"],
                    document_id=row["document_id"],
                    representation_id=(
                        row["representation_id"]
                    ),
                    rank=idx,
                    retrieval_score=row["rrf_score"],
                    semantic_score=row.get(
                        "semantic_score"
                    ),
                    lexical_score=row.get(
                        "lexical_score"
                    ),
                    content=row["content"],
                    location=row.get(
                        "location",
                        {},
                    ),
                    metadata=row.get(
                        "metadata",
                        {},
                    ),
                )

                results.append(result)

            # ====================================================
            # 6. PERSISTÊNCIA
            # ====================================================

            self.result_repo.save_batch(
                results
            )

            # ====================================================
            # 7. FINALIZAÇÃO DA INVESTIGAÇÃO
            # ====================================================

            investigation = (
                self.investigation_repo.update_status(
                    investigation.investigation_id,
                    InvestigationStatus.COMPLETED,
                )
            )

            return investigation, results

        except Exception:

            self.investigation_repo.update_status(
                investigation.investigation_id,
                InvestigationStatus.FAILED,
            )

            raise
