from backend.application.document_processor import DocumentProcessor
from backend.application.segmentation_service import SegmentationService
from backend.domain.repositories import (
    DocumentRepository,
    RetrievalUnitRepository,
    EmbeddingProvider,
)
from backend.domain.entities import DocumentStatus


class PublicationService:

    def __init__(
        self,
        document_repo: DocumentRepository,
        unit_repo: RetrievalUnitRepository,
        processor: DocumentProcessor,
        segmentation_service: SegmentationService,
        embedding_provider: EmbeddingProvider,
    ):
        self.document_repo = document_repo
        self.unit_repo = unit_repo
        self.processor = processor
        self.segmentation_service = segmentation_service
        self.embedding_provider = embedding_provider

    def process_and_publish(
        self,
        document_id: str,
        title: str,
        folder_id: str,
        user_id: str,
        drive_file_id: str,
        file_path: str,
    ):

        self.document_repo.update_status(
            document_id,
            DocumentStatus.PROCESSING,
        )

        try:
            # 1. Fonte física → representação canônica
            representation = self.processor.process_pdf(
                file_path=file_path,
                document_id=document_id,
                metadata={
                    "title": title,
                    "drive_file_id": drive_file_id,
                },
            )

            if not representation.pages:
                raise ValueError(
                    "Documento não produziu conteúdo textual válido."
                )

            # 2. Persistência da representação
            self.document_repo.save_representation(
                document_id,
                representation,
            )

            # 3. Representação → RetrievalUnits
            units = self.segmentation_service.segment(
                representation
            )

            if not units:
                raise ValueError(
                    "Documento não produziu RetrievalUnits."
                )

            # 4. RetrievalUnits → embeddings
            texts = [unit.content for unit in units]

            embeddings = self.embedding_provider.generate_embeddings(
                texts
            )

            if len(embeddings) != len(units):
                raise RuntimeError(
                    "Quantidade de embeddings não corresponde "
                    "às RetrievalUnits."
                )

            # 5. Persistência dos derivados
            self.unit_repo.save_batch(
                units=units,
                embeddings=embeddings,
                user_id=user_id,
                folder_id=folder_id,
            )

            # 6. Só agora o documento pode ser publicado
            self.document_repo.update_status(
                document_id,
                DocumentStatus.ACTIVE,
            )

            return {
                "document_id": document_id,
                "representation_id": representation.representation_id,
                "unit_count": len(units),
                "status": DocumentStatus.ACTIVE.value,
            }

        except Exception:
            # Compensação: nenhuma unidade parcialmente produzida
            # permanece associada a um documento que falhou.
            try:
                self.unit_repo.delete_by_document(document_id)
            finally:
                self.document_repo.update_status(
                    document_id,
                    DocumentStatus.FAILED,
                )

            raise