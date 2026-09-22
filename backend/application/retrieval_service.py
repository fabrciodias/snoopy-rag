import uuid
from typing import List, Optional
from datetime import datetime, timezone
from backend.domain.entities import Investigation, RetrievalResult
from backend.domain.repositories import EmbeddingProvider
from supabase import Client

class RetrievalService:
    """
    Serviço principal de Recuperação Híbrida.
    Garante a separação arquitetural: o resultado da busca (RetrievalResult)
    ainda não é considerado uma Evidência metodológica absoluta.
    """

    def __init__(self, emb_provider: EmbeddingProvider, supabase_client: Client):
        self.emb_provider = emb_provider
        self.client = supabase_client

    def search(self, user_id: str, folder_id: str, query: str, limit: int = 10) -> tuple[Investigation, List[RetrievalResult]]:
        # 1. Cria a entidade Investigação (preserva a pergunta original do usuário)
        investigation = Investigation(
            investigation_id=str(uuid.uuid4()),
            user_id=user_id,
            original_query=query,
            status="PROCESSING",
            created_at=datetime.now(timezone.utc)
        )
        
        db_data = investigation.model_dump(mode="json", exclude_none=True)
        if "investigation_id" in db_data:
            db_data["id"] = db_data.pop("investigation_id")
        
        self.client.table("investigations").insert(db_data).execute()

        # 2. Gera o vetor semântico da pergunta
        query_embeddings = self.emb_provider.generate_embeddings([query])
        if not query_embeddings:
            return investigation, []
            
        vector = query_embeddings[0]

        # 3. Busca bruta simultânea (Lexical + Semantic) via RPC
        response = self.client.rpc("v3_hybrid_search", {
            "p_query_text": query,
            "p_query_embedding": vector,
            "p_match_count": limit * 2, # Trazemos o dobro para a fusão ter margem
            "p_user_id": user_id,
            "p_folder_id": folder_id
        }).execute()

        raw_results = response.data or []

        # 4. FUSION E RERANKING (Materializa a cadeia da V3 no Python)
        # Calcula rankings independentes
        semantic_sorted = sorted(raw_results, key=lambda x: x.get("semantic_score", 0), reverse=True)
        lexical_sorted = sorted(raw_results, key=lambda x: x.get("lexical_score", 0), reverse=True)

        ranks = {}
        for rank, item in enumerate(semantic_sorted):
            ranks.setdefault(item["unit_id"], {})["semantic_rank"] = rank + 1
        for rank, item in enumerate(lexical_sorted):
            ranks.setdefault(item["unit_id"], {})["lexical_rank"] = rank + 1

        # Reciprocal Rank Fusion (RRF) - Constante k=60 é padrão acadêmico
        k = 60
        fused_results = []
        for item in raw_results:
            unit_id = item["unit_id"]
            s_rank = ranks[unit_id].get("semantic_rank", 1000)
            l_rank = ranks[unit_id].get("lexical_rank", 1000)
            
            # Score de fusão
            rrf_score = (1.0 / (k + s_rank)) + (1.0 / (k + l_rank))
            item["rrf_score"] = rrf_score
            fused_results.append(item)

        # 5. SELEÇÃO: Reordena pelo score híbrido e corta no limite exato
        fused_results = sorted(fused_results, key=lambda x: x["rrf_score"], reverse=True)[:limit]

        # 6. Mapeia o retorno para os contratos rígidos de RetrievalResult
        results = []
        for idx, row in enumerate(fused_results):
            result = RetrievalResult(
                result_id=str(uuid.uuid4()),
                investigation_id=investigation.investigation_id,
                unit_id=row["unit_id"],
                rank=idx + 1,               # Agora o rank é injetado corretamente
                retrieval_score=row["rrf_score"], # Score oficial do Híbrido
                metadata={
                    "document_id": row["document_id"],
                    "content": row["content"],
                    "location": row["location"],
                    "raw_semantic_score": row.get("semantic_score", 0),
                    "raw_lexical_score": row.get("lexical_score", 0)
                }
            )
            results.append(result)

        return investigation, results