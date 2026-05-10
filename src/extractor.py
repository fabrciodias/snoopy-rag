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
    test_file = os.path.join(base_dir, 'data', 'raw_pdfs', 'teste.pdf')

    print(f"Iniciando extração. Buscando em: \{test_file}\n")

    metadata, raw_text = extract_pdf_data(test_file)

    if raw_text:
        print("Extração concluída.\n")
        semantic_md = to_markdown(raw_text)
        print("\nTexto em .md Semântico (Início):")
        print(semantic_md[:800])

        output_path = os.path.join(base_dir, 'data', 'markdown', 'teste_processado.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {metadata.get('title', 'Documento sem título')}\n\n")
            f.write(semantic_md)
        print(f"\Arquivo ,md salvo em: {output_path}")
    else:
        print("A extração falhou ou o PDF está em branco")