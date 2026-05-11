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
    md_file = os.path.join(base_dir, 'data', 'markdown', 'teste_processado.md')
    output_file = os.path.join(base_dir, 'data', 'chunks_teste.json')

    if not os.path.exists(md_file):
        print("Arquivo .md não encontrado.")
    else:
        with open(md_file, 'r', encoding='utf-8') as f:
            texto = f.read()
        print("Buscando registro do documento...")
        metadata = get_metadata(texto)

        if metadata:
            metadata["link_drive"] = "https://drive.com/file/d/exemplo_de_link/view"
            print("Realizando o chunking...")
            final_chunks = semantic_chunking(texto, metadata)  

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_chunks, f, indent=4, ensure_ascii=False)
            print(f"Sucesso! Documento dividido em {len(final_chunks)} chunks.")
            print(f"Arquivo salvo em: {output_file}")

            if len(final_chunks) > 10:
                print("\n AMOSTRA DO CHUNK [10]:")
                print("-" * 50)
                print(final_chunks[10]['text'])
                print("-" * 50)
                print("METADADOS:", final_chunks[10]['metadata'])                