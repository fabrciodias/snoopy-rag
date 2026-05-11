import os
import json
from tagger import get_metadata

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
            current_chunk = f"[SEÇÃO: {current_chunk}]\n\n"
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
    md_dir = os.path.join(base_dir, 'data', 'markdown')
    output_file = os.path.join(base_dir, 'data', 'chunks.json')
    map_path = os.path.join(base_dir, 'data', 'drive_links.json')
    
    links_map = {}
    if os.path.exists(map_path):
        with open(map_path, 'r', encoding='utf-8') as f:
            links_map = json.load(f)

    if not os.path.exists(md_dir):
        print(f"[ERRO] Diretório não encontrado: {md_dir}")
        exit()

    final_chunks = []
    print(f"Iniciando processamento no diretório: {md_dir}\n")

    for filename in os.listdir(md_dir):
        if not filename.endswith('.md'):
            continue

        md_file = os.path.join(md_dir, filename)
        origin_name = filename.replace('.md', '.pdf')
        print(f"Processando: {filename}")

        with open(md_file, 'r', encoding='utf-8') as f:
            text = f.read()
        print("Buscando registro de documento (Gemini Tagger)...")
        metadata = get_metadata(text)

        if metadata:
            metadata["link_drive"] = links_map.get(origin_name, "Link não disponível no Drive")
            print("Realizando o chunking semântico...")
            doc_chunks = semantic_chunking(text, metadata)
            
            final_chunks.extend(doc_chunks)
            print(f"{len(doc_chunks)} blocos gerados e adicionados à fila.")
        else:
            print("Falha ao gerar metadados. Pulando arquivo.")
    print("\n" + "="*50)
    if final_chunks:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_chunks, f, indent=4, ensure_ascii=False)
        print(f"[SUCESSO] {len(final_chunks)} chunks consolidadas.")
        print(f"Arquivo salvo em: {output_file}")
    else:
        print("Nenhum chunk gerado. A pasta markdown estava vazia ou deu erro no Tagger.")