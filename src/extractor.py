import fitz
import os
import re

def extract_pdf_data(file_path):
    metadata = {}
    text = ""
    if not os.path.exists(file_path):
        print(f"[ERROR] Arquivo não encontrado: {file_path}")
        return metadata, text
        
    try:
        pdf_document = fitz.open(file_path)
        metadata = {k: v for k, v in pdf_document.metadata.items()}
        for page in pdf_document:
            blocks = page.get_text("blocks")
            for b in blocks:
                if b[6] == 0:
                    block_text = re.sub(r' {2,}', ' ', b[4].strip().replace('\n', ' '))
                    if block_text:
                        text += block_text + "\n\n"
        pdf_document.close()
    except Exception as e:
        print(f"[ERRO] Falha ao ler '{file_path}': {e}")
        
    return metadata, text