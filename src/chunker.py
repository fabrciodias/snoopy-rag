def semantic_chunking(markdown_text, doc_metadata, max_len=1500):
    paragraphs = markdown_text.split('\n\n')
    chunks = []
    current_chunk = ""
    current_section = "Introdução/Contexto Geral"

    for p in paragraphs:
        p = p.strip()
        if not p: continue
        
        # Inicia nova seção
        if p.startswith('##'):
            current_section = p.replace('##', '').strip()[:150]
            if len(current_chunk) > 300:
                chunks.append({"text": current_chunk.strip(), "metadata": {**doc_metadata, "secao": current_section}})
                current_chunk = ""
            current_chunk = f"[SEÇÃO: {current_section}]\n\n"
            continue
            
        # Agrupa parágrafos
        if len(current_chunk) + len(p) > max_len and len(current_chunk) > 50:
            chunks.append({"text": current_chunk.strip(), "metadata": {**doc_metadata, "secao": current_section}})
            current_chunk = f"[SEÇÃO: {current_section}]\n\n{p}\n\n"
        else:
            current_chunk += f"{p}\n\n"
            
    # Finaliza último chunk
    if current_chunk.strip() and not current_chunk.strip().endswith(f"[SEÇÃO: {current_section}]"):
        chunks.append({"text": current_chunk.strip(), "metadata": {**doc_metadata, "secao": current_section}})
        
    return chunks