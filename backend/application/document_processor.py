import uuid
from typing import Any, Dict, Optional

import fitz

from backend.domain.entities import (
    DocumentBlock,
    DocumentPage,
    DocumentRepresentation,
)


class DocumentProcessor:
    """
    Processador de documentos da V3.

    Transforma o PDF físico em uma representação estruturada,
    preservando páginas, blocos, ordem de leitura e geometria
    espacial dos elementos extraídos.
    """

    def process_pdf(
        self,
        file_path: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentRepresentation:

        if metadata is None:
            metadata = {}

        try:
            doc = fitz.open(file_path)

        except Exception as error:
            raise RuntimeError(
                f"Falha ao abrir o ficheiro PDF "
                f"'{file_path}': {error}"
            ) from error

        try:
            pdf_metadata = doc.metadata or {}

            representation_metadata = {
                **pdf_metadata,
                **metadata,
            }

            pages = []

            for page_num, page in enumerate(doc):
                raw_blocks = page.get_text("blocks")

                document_blocks = []

                for block in raw_blocks:

                    x0, y0, x1, y1, text, block_number, block_type = (
                        block[:7]
                    )

                    clean_text = " ".join(
                        text.strip().split()
                    )

                    # Neste estágio a representação continua
                    # orientada ao conteúdo textual recuperável.
                    if not clean_text:
                        continue

                    document_blocks.append(
                        DocumentBlock(
                            block_index=int(
                                block_number
                            ),
                            text=clean_text,
                            block_type=(
                                "text"
                                if block_type == 0
                                else str(block_type)
                            ),
                            x0=float(x0),
                            y0=float(y0),
                            x1=float(x1),
                            y1=float(y1),
                        )
                    )

                if document_blocks:
                    pages.append(
                        DocumentPage(
                            page_number=page_num + 1,
                            width=float(
                                page.rect.width
                            ),
                            height=float(
                                page.rect.height
                            ),
                            blocks=document_blocks,
                        )
                    )

            return DocumentRepresentation(
                representation_id=str(
                    uuid.uuid4()
                ),
                document_id=document_id,
                pages=pages,
                metadata=representation_metadata,
            )

        finally:
            doc.close()
