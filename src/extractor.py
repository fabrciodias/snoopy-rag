import fitz
import os
import re

def extract_pdf_data(file_path):
    metadata = {}
    text = ""

    # Verifica se o arquivo existe antes de abrir
    if not os.path.exists(file_path):
        print(f"[ERROR] Arquivo não encontrado: {file_path}")
        return metadata, text
        
    try:
        # Abre o documento e captura metadados (autor, título, etc.)
        doc = fitz.open(file_path)
        metadata = {k: v for k, v in doc.metadata.items()}
        
        for page in doc:
            # Extrai blocos de texto (b[6] == 0 filtra apenas texto, ignorando imagens/vetores)
            for b in page.get_text("blocks"):
                if b[6] == 0:
                    # Normaliza espaços múltiplos e limpa quebras de linha dentro do bloco
                    line = re.sub(r' {2,}', ' ', b[4].strip().replace('\n', ' '))
                    if line:
                        text += line + "\n\n"
        
        doc.close()
    except Exception as e:
        print(f"[ERRO] Falha ao processar PDF: {e}")
        
    return metadata, text