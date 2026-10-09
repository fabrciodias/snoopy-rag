from backend.application.bibliographic_metadata_extractor import (
    BibliographicMetadataExtractor,
)
from backend.application.document_processor import (
    DocumentProcessor,
)
from backend.application.segmentation_service import (
    SegmentationService,
)
from backend.domain.entities import (
    BibliographicMetadata,
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
        metadata_extractor: BibliographicMetadataExtractor,
    ):
        self.document_repo = document_repo
        self.unit_repo = unit_repo
        self.processor = processor
        self.segmentation_service = segmentation_service
        self.embedding_provider = embedding_provider
        self.metadata_extractor = metadata_extractor

    def process_and_publish(
        self,
        document: Document,
        file_path: str,
    ):
        """
        Processa uma fonte documental e publica sua representação
        somente depois que todos os derivados necessários estiverem
        prontos.

        A extração bibliográfica ocorre sobre a representação
        textual, e não sobre o nome do arquivo.

        Para um documento já ACTIVE, a versão corrente permanece
        intacta durante o processamento.

        Em caso de falha:
            - documento ACTIVE permanece ACTIVE;
            - documento ainda não publicado passa a FAILED;
            - nenhuma unidade histórica existente é removida.
        """

        previous_status = document.status

        if previous_status != DocumentStatus.ACTIVE:
            self.document_repo.update_status(
                document.document_id,
                DocumentStatus.PROCESSING,
            )

        try:
            # ====================================================
            # 1. Fonte física -> representação canônica
            # ====================================================

            representation = self.processor.process_pdf(
                file_path=file_path,
                document_id=document.document_id,
                metadata={
                    "drive_file_id": document.drive_file_id,
                    "drive_file_name": document.drive_file_name,
                    "drive_link": document.drive_link,
                    "mime_type": document.mime_type,
                    "document_hash": document.document_hash,
                },
            )

            if not representation.pages:
                raise ValueError(
                    "Documento não produziu conteúdo textual válido."
                )

            # ====================================================
            # 2. Representação -> metadados bibliográficos
            # ====================================================

            bibliographic_metadata = (
                self.metadata_extractor.extract(
                    representation
                )
            )

            document = self._apply_bibliographic_metadata(
                document=document,
                metadata=bibliographic_metadata,
            )

            # Preserva os metadados técnicos obtidos do PDF e
            # registra os metadados bibliográficos separadamente.
            representation.metadata[
                "bibliographic"
            ] = bibliographic_metadata.model_dump(
                mode="json"
            )

            # ====================================================
            # 3. Representação -> RetrievalUnits
            # ====================================================

            units = self.segmentation_service.segment(
                representation
            )

            if not units:
                raise ValueError(
                    "Documento não produziu RetrievalUnits."
                )

            # ====================================================
            # 4. RetrievalUnits -> embeddings
            # ====================================================

            texts = [
                unit.content
                for unit in units
            ]

            embeddings = (
                self.embedding_provider.generate_embeddings(
                    texts
                )
            )

            if len(embeddings) != len(units):
                raise RuntimeError(
                    "Quantidade de embeddings não corresponde "
                    "às RetrievalUnits."
                )

            # ====================================================
            # 5. Persistência da representação candidata
            # ====================================================

            self.document_repo.save_representation(
                document.document_id,
                representation,
            )

            # ====================================================
            # 6. Persistência dos derivados
            # ====================================================

            self.unit_repo.save_batch(
                units=units,
                embeddings=embeddings,
            )

            # ====================================================
            # 7. Publicação
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
                "status": DocumentStatus.ACTIVE.value,
            }

        except Exception:
            # Uma falha durante a atualização não deve substituir
            # a representação que já estava publicada.
            if previous_status != DocumentStatus.ACTIVE:
                self.document_repo.update_status(
                    document.document_id,
                    DocumentStatus.FAILED,
                )

            raise

    @staticmethod
    def _apply_bibliographic_metadata(
        document: Document,
        metadata: BibliographicMetadata,
    ) -> Document:
        """
        Aplica os campos identificados pelo extrator.

        O nome físico do arquivo nunca é usado como título
        bibliográfico apenas por estar disponível.

        Quando um campo não é identificado, preserva-se um valor
        bibliográfico anterior somente se ele não for apenas
        o nome do arquivo.
        """

        extracted_title = (
            metadata.title.strip()
            if metadata.title
            else None
        )

        existing_title = (
            document.title.strip()
            if document.title
            else None
        )

        drive_file_name = (
            document.drive_file_name.strip()
            if document.drive_file_name
            else None
        )

        # Um título antigo que seja idêntico ao nome do arquivo
        # não é considerado evidência bibliográfica.
        if (
            existing_title
            and drive_file_name
            and existing_title.casefold()
            == drive_file_name.casefold()
        ):
            existing_title = None

        title = (
            extracted_title
            or existing_title
            or "Título não identificado"
        )

        return document.model_copy(
            update={
                "title": title,
                "authors": (
                    metadata.authors
                    if metadata.authors
                    else document.authors
                ),
                "publication_year": (
                    metadata.publication_year
                    or document.publication_year
                ),
                "document_type": (
                    metadata.document_type
                    or document.document_type
                ),
                "language": (
                    metadata.language
                    or document.language
                ),
                "keywords": (
                    metadata.keywords
                    if metadata.keywords
                    else document.keywords
                ),
            }
        )