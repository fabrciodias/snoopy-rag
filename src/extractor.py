import fitz
import os
import re
import shutil

def extract_pdf_data(file_path):
    metadata = {}
    text = ""

    if not os.path.exists(file_path):
        print(f"[ERROR] Arquivo não encontrado em: {file_path}")
        return metadata, text
    
    try:
        pdf_document = fitz.open(file_path)
        for key, value in pdf_document.metadata.items():
            metadata[key] = value

        for page in pdf_document:
            blocks = page.get_text("blocks")
            for b in blocks:
                if b[6] == 0:
                    block_text = b[4].strip()
                    block_text = block_text.replace('\n', ' ')
                    block_text = re.sub(r' {2,}', ' ', block_text)

                    if block_text:
                        text += block_text + "\n\n"

        pdf_document.close()

    except Exception as e:
        print(f"[ERRO] Não foi possível ler o arquivo '{file_path}'. Motivo: {e}")

    return metadata, text

if __name__ == '__main__':
    from cleaner import to_markdown

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_pdfs = os.path.join(base_dir, 'data', 'raw_pdfs')
    docs_dir = os.path.join(base_dir, 'data', 'documents')

    os.makedirs(docs_dir, exist_ok=True)
    print(f"Iniciando extração. Buscando em: \{raw_pdfs}\n")

    for filename in os.listdir(raw_pdfs):
        if not filename.lower().endswith('.pdf'):
            continue

        src_path = os.path.join(raw_pdfs, filename)
        folder_name = filename[:-4].strip()
        doc_folder = os.path.join(docs_dir, folder_name)

        pdf_path = os.path.join(doc_folder, 'source.pdf')
        md_path = os.path.join(doc_folder, 'semantic.md')

        if os.path.exists(md_path):
            print(f"Pulando: '{folder_name}' já existe")
            continue
        print(f"Criando: {folder_name}...")
        os.makedirs(doc_folder, exist_ok=True)
        
        shutil.copy2(src_path, pdf_path)
        print("Lendo e extraindo texto bruto...")
        metadata, raw_text = extract_pdf_data(src_path)

        if raw_text:
            print("Limpando e formatando para Markdown semântico...")
            semantic_md = to_markdown(raw_text)

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# {metadata.get('title', 'Documento sem título')}\n\n")
                f.write(semantic_md)
            print("Extração concluída")
        else:
            print("A extração falhou. O PDF pode estar corrompido ou ser apenas imagens")
    print("\nProcesso de extração e estruturação finalizado.")