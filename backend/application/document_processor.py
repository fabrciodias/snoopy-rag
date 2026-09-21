import fitz  
import uuid
from typing import Dict, Any, Optional
from backend.domain.entities import DocumentRepresentation, DocumentPage, DocumentBlock

class DocumentProcessor:
    """
    Processador de documentos da V3 Alpha.
    Responsável por ler a fonte física (ficheiro PDF) e transformá-la na representação
    canónica estruturada (DocumentRepresentation), preservando páginas, blocos e ordem
    de leitura. Abandona o achatamento destrutivo para Markdown da versão anterior.
    """

    def process_pdf(self, file_path: str, document_id: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentRepresentation:
        if metadata is None:
            metadata = {}
            
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise RuntimeError(f"Falha ao abrir o ficheiro PDF '{file_path}': {str(e)}")

        pages = []
        
        # Extrai os metadados nativos do PDF para enriquecer o contexto da representação
        pdf_metadata = doc.metadata or {}
        metadata.update(pdf_metadata)
        
        for page_num, page in enumerate(doc):
            # O método get_text("blocks") extrai blocos mantendo a geometria espacial.
            # Retorna tuplos no formato: (x0, y0, x1, y1, texto, numero_do_bloco, tipo_do_bloco)
            raw_blocks = page.get_text("blocks")
            document_blocks = []
            
            for b_index, b in enumerate(raw_blocks):
                # O tipo 0 identifica blocos de texto (o tipo 1 corresponde a imagens)
                if b[6] == 0:
                    # Limpeza mínima: remove espaços duplos e quebras de linha excessivas
                    clean_text = " ".join(b[4].strip().split())
                    
                    if clean_text:
                        document_blocks.append(
                            DocumentBlock(
                                block_index=b_index,
                                text=clean_text,
                                block_type="text"
                            )
                        )
                        
            if document_blocks:
                pages.append(
                    DocumentPage(
                        page_number=page_num + 1,
                        blocks=document_blocks
                    )
                )
                
        doc.close()
        
        return DocumentRepresentation(
            representation_id=str(uuid.uuid4()),
            document_id=document_id,
            pages=pages,
            metadata=metadata
        )