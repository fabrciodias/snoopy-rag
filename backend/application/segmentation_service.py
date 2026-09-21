from typing import List
from backend.domain.entities import DocumentRepresentation, RetrievalUnit

class SegmentationService:
    """
    Serviço responsável por fatiar a Representação Canônica do documento
    em Unidades de Recuperação (RetrievalUnits).
    Substitui a lógica frágil baseada em regex do antigo chunker.py, 
    garantindo que cada fragmento mantenha sua rastreabilidade espacial exata
    (página e bloco) de volta à fonte original.
    """
    
    def __init__(self, max_words_per_unit: int = 250):
        # 250 palavras é um bom padrão heurístico para manter a densidade
        # semântica alta para o modelo de embeddings (geralmente ~350 a 500 tokens).
        self.max_words_per_unit = max_words_per_unit

    def segment(self, representation: DocumentRepresentation) -> List[RetrievalUnit]:
        units = []
        current_text = []
        current_word_count = 0
        
        # Rastreadores de proveniência espacial
        start_page = None
        start_block = None
        unit_index = 0
        
        for page in representation.pages:
            for block in page.blocks:
                # Marca a origem se estivermos abrindo uma nova unidade
                if start_page is None:
                    start_page = page.page_number
                    start_block = block.block_index
                    
                words = block.text.split()
                current_text.append(block.text)
                current_word_count += len(words)
                
                # Se o "balde" encheu, empacotamos a RetrievalUnit
                if current_word_count >= self.max_words_per_unit:
                    units.append(
                        RetrievalUnit(
                            document_id=representation.document_id,
                            representation_id=representation.representation_id,
                            unit_index=unit_index,
                            content="\n\n".join(current_text),
                            location={
                                "start_page": start_page,
                                "end_page": page.page_number,
                                "start_block": start_block,
                                "end_block": block.block_index
                            },
                            section="Geral", # Ponto de evolução: detectar blocos do tipo "heading"
                            metadata=representation.metadata
                        )
                    )
                    
                    # Reseta o balde para o próximo bloco
                    unit_index += 1
                    current_text = []
                    current_word_count = 0
                    start_page = None
                    start_block = None
                    
        # Recolhe o fragmento residual (o finalzinho do documento que não encheu o balde)
        if current_text:
            end_page = representation.pages[-1].page_number if representation.pages else 1
            end_block = representation.pages[-1].blocks[-1].block_index if representation.pages and representation.pages[-1].blocks else 0
            
            units.append(
                RetrievalUnit(
                    document_id=representation.document_id,
                    representation_id=representation.representation_id,
                    unit_index=unit_index,
                    content="\n\n".join(current_text),
                    location={
                        "start_page": start_page,
                        "end_page": end_page,
                        "start_block": start_block,
                        "end_block": end_block
                    },
                    section="Geral",
                    metadata=representation.metadata
                )
            )
            
        return units