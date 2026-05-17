# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

def semantic_chunking(markdown_text, doc_metadata, max_len=1500):
    paragraphs = markdown_text.split('\n\n')
    chunks = []
    current_chunk = ""
    current_section = "Introdução/Contexto Geral"

    for p in paragraphs:
        p = p.strip()
        if not p: continue
        
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