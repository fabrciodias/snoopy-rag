import fitz
import os
import re

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
    md_dir = os.path.join(base_dir, 'data', 'markdown')

    os.makedirs(md_dir, exist_ok=True)
    print(f"Iniciando extração. Buscando em: \{raw_pdfs}\n")

    for filename in os.listdir(raw_pdfs):
        if not filename.lower().endswith('.pdf'):
            continue

        pdf_path = os.path.join(raw_pdfs, filename)
        md_filename = filename[:-4] + '.md'
        md_path = os.path.join(md_dir, md_filename)

        if os.path.exists(md_path):
            print(f"Pulando extração: {filename} (já existe o .md correspondente)")
            continue
        print(f"Lendo PDF: {filename}...")
        metadata, raw_text = extract_pdf_data(pdf_path)

        if raw_text:
            print("Limpando e formatando para Markdown semântico...")
            semantic_md = to_markdown(raw_text)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# {metadata.get('title', 'Documento sem título')}\n\n")
                f.write(semantic_md)
            print(f"Salvo como: {md_filename}")
        else:
            print(f"A extração falhou ou o PDF {filename} está em branco.")
    print("\nProcesso de extração finalizado.")