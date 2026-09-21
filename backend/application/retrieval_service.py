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
        self.client = supabase_client  # Acesso direto para execução da RPC

    def search(self, user_id: str, folder_id: str, query: str, limit: int = 10) -> tuple[Investigation, List[RetrievalResult]]:
        # 1. Cria a entidade Investigação (preserva a pergunta original do usuário)
        investigation = Investigation(
            investigation_id=str(uuid.uuid4()),
            user_id=user_id,
            original_query=query,
            status="PROCESSING",
            created_at=datetime.now(timezone.utc)
        )
        
        # Prepara os dados convertendo o nome do ID para o padrão esperado pelo Supabase
        db_data = investigation.model_dump(mode="json", exclude_none=True)
        if "investigation_id" in db_data:
            db_data["id"] = db_data.pop("investigation_id")
        
        # O backend salva o estado da investigação no banco
        self.client.table("investigations").insert(db_data).execute()

        # 2. Gera o vetor semântico da pergunta
        query_embeddings = self.emb_provider.generate_embeddings([query])
        if not query_embeddings:
            return investigation, []
            
        vector = query_embeddings[0]

        # 3. Executa a Recuperação Híbrida (Fusion) direto no banco
        response = self.client.rpc("v3_hybrid_search", {
            "p_query_text": query,
            "p_query_embedding": vector,
            "p_match_count": limit,
            "p_user_id": user_id,
            "p_folder_id": folder_id
        }).execute()

        # 4. Mapeia o retorno cru para contratos rígidos de RetrievalResult
        results = []
        for idx, row in enumerate(response.data or []):
            result = RetrievalResult(
                result_id=str(uuid.uuid4()),
                investigation_id=investigation.investigation_id,
                unit_id=row["unit_id"],
                rank=row["rank"] or (idx + 1),
                retrieval_score=row["similarity"],
                metadata={
                    "document_id": row["document_id"],
                    "content": row["content"],
                    "location": row["location"]
                }
            )
            results.append(result)

        return investigation, results