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
        doc_processor: DocumentProcessor,
        seg_service: SegmentationService,
        doc_repo: DocumentRepository,
        unit_repo: RetrievalUnitRepository,
        emb_provider: EmbeddingProvider
    ):
        self.doc_processor = doc_processor
        self.seg_service = seg_service
        self.doc_repo = doc_repo
        self.unit_repo = unit_repo
        self.emb_provider = emb_provider

    def process_and_publish(self, file_path: str, document_id: str, title: str, folder_id: str, user_id: str, drive_file_id: str) -> None:
        try:
            # 1. Gerar Hash de Segurança
            with open(file_path, "rb") as f:
                doc_hash = hashlib.md5(f.read()).hexdigest()

            # 2. Registar o documento como PROCESSING
            self.doc_repo.create_or_update(
                document_id=document_id, title=title, folder_id=folder_id, 
                user_id=user_id, drive_file_id=drive_file_id, document_hash=doc_hash
            )

            # 3. Fase 2: Extrair a Representação Canónica
            representation = self.doc_processor.process_pdf(file_path, document_id)

            # 4. Fase 3: Segmentar com rigor espacial
            units = self.seg_service.segment(representation)

            # 5. Fase 4: Vetorização e Persistência em Lotes
            batch_size = 5
            for i in range(0, len(units), batch_size):
                batch_units = units[i : i + batch_size]
                texts = [u.content for u in batch_units]
                
                # Gera os Embeddings
                embeddings = self.emb_provider.generate_embeddings(texts)
                
                # Grava no Supabase (chunks)
                self.unit_repo.save_batch(batch_units, embeddings, user_id, folder_id)

            # 6. Publicação Atómica (Opcional na V2, Obrigatório na V3)
            self.doc_repo.update_status(document_id, DocumentStatus.ACTIVE)

        except Exception as e:
            # Em caso de qualquer erro crítico, o documento é marcado como FAILED
            # e a exceção é repassada para que a Operation (Fase 1) registre o log.
            self.doc_repo.update_status(document_id, DocumentStatus.FAILED)
            raise e
            
        finally:
            # Limpeza do ficheiro físico (mantendo o rigor do LPP-Acervo)
            if os.path.exists(file_path):
                os.remove(file_path)