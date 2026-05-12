import fitz
import os
import re
import json
import sys

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
    state_path = os.path.join(base_dir, 'data', 'drive_state.json')

    os.makedirs(docs_dir, exist_ok=True)
    if not os.path.exists(state_path):
        print("[ERRO] drive_state.json não encontrado. Rode o drive_sync primeiro.")
        sys.exit(1)

    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
        
    print(f"Iniciando extração. Buscando arquivos pendentes...\n")
    processed_files = 0
    modified_state = False
 
    for file_id, file_info in state.items():
        if file_info.get('status') == 'pendente_extracao':
            filename = file_info.get('name')
            src_path = os.path.join(raw_pdfs, filename)

            if not os.path.exists(src_path):
                print(f"[AVISO] PDF pendente não encontrado no disco: {filename}")
                continue

            folder_name = filename[:-4].strip()
            doc_folder = os.path.join(docs_dir, folder_name)
            md_path = os.path.join(doc_folder, 'semantic.md')

            print(f"Criando: {folder_name}...")
            os.makedirs(doc_folder, exist_ok=True)

            try:
                print("Lendo e extraindo texto bruto...")
                metadata, raw_text = extract_pdf_data(src_path)

                if raw_text:
                    print("Limpando e formatando para Markdown semântico...")
                    semantic_md = to_markdown(raw_text)

                    with open(md_path, 'w', encoding='utf-8') as f:
                        title = metadata.get('title', '')
                        if not title or str(title).strip() == '' or str(title).lower() == 'untitled':
                            title = folder_name
                        f.write(f"# {title}\n\n")
                        f.write(semantic_md)
                        
                    if os.path.exists(src_path):
                        os.remove(src_path)

                    state[file_id]['status'] = 'processado'
                    processed_files += 1
                    modified_state = True
                
                    print("Extração concluída. PDF original deletado do disco.\n")
                else:
                    print("A extração falhou. O PDF pode estar corrompido ou ser apenas imagens.")
                    state[file_id]['status'] = 'falha_extracao'
                    modified_state = True
            except Exception as e:
                print(f"[ERRO CRÍTICO] Falha ao processar o arquivo '{filename}': {e}")
                state[file_id]['status'] = 'falha_extracao'
                modified_state = True

    if modified_state:
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        print(f"Processo de extração finalizado. {processed_files} arquivos processados com sucesso.")
    else:
        print("\nProcesso finalizado. Nenhum arquivo foi alterado.")