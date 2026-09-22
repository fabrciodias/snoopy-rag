import os
import hashlib
from typing import Optional
from backend.application.document_processor import DocumentProcessor
from backend.application.segmentation_service import SegmentationService
from backend.domain.repositories import DocumentRepository, RetrievalUnitRepository, EmbeddingProvider
from backend.domain.entities import DocumentStatus

class PublicationService:
    """
    Serviço que orquestra o ciclo de vida da publicação de um documento na V3.
    Garante a regra de Ouro: Um documento só se torna ACTIVE se todos os blocos,
    embeddings e metadados forem gravados com sucesso.
    """
    
    def __init__(
        self, 
        document_repo, 
        unit_repo, 
        processor, 
        segmentation_service, 
        embedding_provider
    ):
        self.document_repo = document_repo
        self.unit_repo = unit_repo
        self.processor = processor
        self.segmentation_service = segmentation_service
        self.embedding_provider = embedding_provider

    def process_and_publish(self, document_id: str, user_id: str, folder_id: str, file_path: str):
        try:
            # 1. Trava o estado para PROCESSING
            self.document_repo.update_status(document_id, DocumentStatus.PROCESSING)
            
            # 2. Extrai e guarda a Representação Canónica
            representation = self.processor.extract(file_path, document_id)
            self.document_repo.save_representation(document_id, representation)
            
            # 3. Segmenta de forma governada
            units = self.segmentation_service.segment(representation)
            
            # 4. Gera Embeddings
            texts_to_embed = [unit.content for unit in units]
            embeddings = self.embedding_provider.generate_embeddings(texts_to_embed)
            
            # 5. Persiste as Unidades + Embeddings (O FTS será gerado via trigger ou persistência SQL do Supabase)
            self.unit_repo.save_batch(units, embeddings, user_id, folder_id)
            
            # 6. Publicação Coerente: Só agora vai para ACTIVE
            self.document_repo.update_status(document_id, DocumentStatus.ACTIVE)
            
        except Exception as e:
            # Em caso de falha em qualquer etapa (extração, LLM timeout, erro no pgvector), reverte o estado lógico
            self.document_repo.update_status(document_id, DocumentStatus.FAILED)
            # A operação assíncrona (Operation) registará o erro no seu próprio fluxo
            raise e