import os
import json

def semantic_chunking(markdown_text, doc_metadata, max_len=1500):
    paragraphs = markdown_text.split('\n\n')
    chunks = []
    current_chunk = ""
    current_section = "Introdução/Contexto Geral"

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        
        if p.startswith('##'):
            current_section = p.replace('##', '').replace('\n', ' ').strip()[:150]
            if len(current_chunk) > 300:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {**doc_metadata, "secao": current_section}
                })
                current_chunk = ""
            current_chunk = f"[SEÇÃO: {current_section}]\n\n"
            continue
        if len(current_chunk) + len(p) > max_len and len(current_chunk) > len(f"[SEÇÃO: {current_section}]\n\n"):
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {**doc_metadata, "secao": current_section}
            })
            current_chunk = f"[SEÇÃO: {current_section}]\n\n{p}\n\n"
        else:
            current_chunk += p + "\n\n"
    if current_chunk.strip() and current_chunk.strip() != f"[SEÇÃO: {current_section}]":
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {**doc_metadata, "secao": current_section}
        })
    return chunks

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, 'data', 'documents')
    output_file = os.path.join(base_dir, 'data', 'chunks.jsonl')
    
    if not os.path.exists(docs_dir):
        print(f"[ERRO] Diretório não encontrado: {docs_dir}")
        exit()
    print(f"Iniciando processamento em: {docs_dir}\n")

    with open(output_file, 'w', encoding='utf-8') as f:
        pass
    total_chunks = 0

    for folder_name in os.listdir(docs_dir):
        doc_folder = os.path.join(docs_dir, folder_name)
        if not os.path.isdir(doc_folder):
            continue

        md_file = os.path.join(doc_folder, 'semantic.md')
        meta_file = os.path.join(doc_folder, 'metadata.json')
        if not os.path.exists(md_file) or not os.path.exists(meta_file):
            print(f"Aviso: Arquivos faltando em '{folder_name}'. Pulando.")
            continue
        print(f"Processando '{folder_name}'")

        with open(md_file, 'r', encoding='utf-8') as f:
            text = f.read()
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print("Realizando chunking...")

        doc_chunks = semantic_chunking(text, metadata)
        with open(output_file, 'a', encoding='utf-8') as f_out:
            for chunk in doc_chunks:
                f_out.write(json.dumps(chunk, ensure_ascii=False) + '\n')
                total_chunks += 1
        print(f"{len(doc_chunks)} blocos gerados e adicionados à fila.")

    print("\n" + "="*50)
    if total_chunks > 0:
        print(f"[SUCESSO] {total_chunks} chunks consolidado no arquivo mestre.")
        print(f"Arquivo salvo em: {output_file}")
    else:    
        print("Nenhum chunk gerado. A pasta markdown estava vazia ou deu erro no Tagger.")