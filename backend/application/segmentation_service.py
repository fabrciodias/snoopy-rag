from typing import List, Optional

from backend.domain.entities import (
    DocumentBlock,
    DocumentLocation,
    DocumentRepresentation,
    RetrievalUnit,
)


class SegmentationService:
    """
    Converte uma DocumentRepresentation em RetrievalUnits.

    A segmentação continua sendo heurística nesta etapa.
    O objetivo aqui é preservar corretamente a proveniência
    estrutural e espacial de cada unidade.
    """

    def __init__(
        self,
        max_words_per_unit: int = 250,
    ):
        self.max_words_per_unit = (
            max_words_per_unit
        )

    @staticmethod
    def _location_from_blocks(
        start_page: int,
        start_block: DocumentBlock,
        end_page: int,
        end_block: DocumentBlock,
    ) -> DocumentLocation:

        return DocumentLocation(
            start_page=start_page,
            end_page=end_page,
            start_block=start_block.block_index,
            end_block=end_block.block_index,
            start_x0=start_block.x0,
            start_y0=start_block.y0,
            start_x1=start_block.x1,
            start_y1=start_block.y1,
            end_x0=end_block.x0,
            end_y0=end_block.y0,
            end_x1=end_block.x1,
            end_y1=end_block.y1,
        )

    def segment(
        self,
        representation: DocumentRepresentation,
    ) -> List[RetrievalUnit]:

        units: List[RetrievalUnit] = []

        current_text: List[str] = []
        current_word_count = 0

        start_page: Optional[int] = None
        start_block: Optional[DocumentBlock] = None

        last_page: Optional[int] = None
        last_block: Optional[DocumentBlock] = None

        unit_index = 0

        for page in representation.pages:

            for block in page.blocks:

                if start_page is None:
                    start_page = page.page_number
                    start_block = block

                current_text.append(block.text)

                current_word_count += len(
                    block.text.split()
                )

                last_page = page.page_number
                last_block = block

                if (
                    current_word_count
                    >= self.max_words_per_unit
                ):
                    units.append(
                        RetrievalUnit(
                            document_id=(
                                representation.document_id
                            ),
                            representation_id=(
                                representation.representation_id
                            ),
                            unit_index=unit_index,
                            content="\n\n".join(
                                current_text
                            ),
                            location=(
                                self._location_from_blocks(
                                    start_page,
                                    start_block,
                                    last_page,
                                    last_block,
                                )
                            ),
                            section="Geral",
                            metadata=(
                                representation.metadata
                            ),
                        )
                    )

                    unit_index += 1

                    current_text = []
                    current_word_count = 0

                    start_page = None
                    start_block = None
                    last_page = None
                    last_block = None

        # ========================================================
        # Fragmento residual
        # ========================================================

        if (
            current_text
            and start_page is not None
            and start_block is not None
            and last_page is not None
            and last_block is not None
        ):
            units.append(
                RetrievalUnit(
                    document_id=(
                        representation.document_id
                    ),
                    representation_id=(
                        representation.representation_id
                    ),
                    unit_index=unit_index,
                    content="\n\n".join(
                        current_text
                    ),
                    location=(
                        self._location_from_blocks(
                            start_page,
                            start_block,
                            last_page,
                            last_block,
                        )
                    ),
                    section="Geral",
                    metadata=representation.metadata,
                )
            )

        return units
