from backend.application.document_processor import (
    DocumentProcessor,
)
from backend.application.segmentation_service import (
    SegmentationService,
)
from backend.domain.entities import (
    Document,
    DocumentStatus,
)
from backend.domain.repositories import (
    DocumentRepository,
    EmbeddingProvider,
    RetrievalUnitRepository,
)


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
        document: Document,
        file_path: str,
    ):
        """
        Processa uma nova fonte documental e publica sua representação
        somente depois que todos os derivados necessários estiverem
        prontos.

        Para um documento já ACTIVE, a versão corrente permanece
        intacta durante todo o processamento.

        Em caso de falha:
            - documento ACTIVE permanece ACTIVE;
            - documento ainda não publicado passa a FAILED;
            - nenhuma unidade histórica existente é removida.
        """

        previous_status = document.status

        # Um documento novo pode entrar em PROCESSING.
        # Um documento já ACTIVE continua ACTIVE até a publicação.
        if previous_status != DocumentStatus.ACTIVE:
            self.document_repo.update_status(
                document.document_id,
                DocumentStatus.PROCESSING,
            )

        try:
            # ====================================================
            # 1. Fonte física → representação canônica
            # ====================================================

            representation = self.processor.process_pdf(
                file_path=file_path,
                document_id=document.document_id,
                metadata={
                    "title": document.title,
                    "drive_file_id": document.drive_file_id,
                },
            )

            if not representation.pages:
                raise ValueError(
                    "Documento não produziu conteúdo textual válido."
                )

            # ====================================================
            # 2. Representação → RetrievalUnits
            # ====================================================

            units = self.segmentation_service.segment(
                representation
            )

            if not units:
                raise ValueError(
                    "Documento não produziu RetrievalUnits."
                )

            # ====================================================
            # 3. RetrievalUnits → embeddings
            # ====================================================

            texts = [
                unit.content
                for unit in units
            ]

            embeddings = (
                self.embedding_provider
                .generate_embeddings(texts)
            )

            if len(embeddings) != len(units):
                raise RuntimeError(
                    "Quantidade de embeddings não corresponde "
                    "às RetrievalUnits."
                )

            # ====================================================
            # 4. Persistência da representação candidata
            # ====================================================

            self.document_repo.save_representation(
                document.document_id,
                representation,
            )

            # ====================================================
            # 5. Persistência dos derivados
            # ====================================================

            self.unit_repo.save_batch(
                units=units,
                embeddings=embeddings,
            )

            # ====================================================
            # 6. Publicação
            # ====================================================

            published_document = (
                self.document_repo.publish_representation(
                    document=document,
                    representation=representation,
                )
            )

            return {
                "document_id": (
                    published_document.document_id
                ),
                "representation_id": (
                    representation.representation_id
                ),
                "unit_count": len(units),
                "status": (
                    DocumentStatus.ACTIVE.value
                ),
            }

        except Exception:
            # ====================================================
            # Falha segura
            # ====================================================
            #
            # Não removemos unidades.
            #
            # Se já existia uma publicação ACTIVE, ela permanece
            # intacta. Os derivados parcialmente criados pertencem
            # à representação candidata e poderão ser tratados
            # posteriormente por uma rotina de limpeza.
            #
            if previous_status != DocumentStatus.ACTIVE:
                self.document_repo.update_status(
                    document.document_id,
                    DocumentStatus.FAILED,
                )

            raise