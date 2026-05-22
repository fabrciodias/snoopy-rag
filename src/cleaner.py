import re
from collections import Counter

def to_markdown(raw_text):
    if not raw_text: 
        return ""
    
    # 1. Remove sumários e pontilhados cegos (ex: "Introdução ........... 5")
    text = re.sub(r'\.{4,}', ' ', raw_text)
    
    # 2. Identifica e remove cabeçalhos/rodapés repetitivos da paginação
    paragraphs = text.split('\n\n')
    block_counts = Counter(p.strip() for p in paragraphs if len(p.strip()) > 15)
    repetitive_blocks = {p for p, count in block_counts.items() if count > 3}
    
    clean_paragraphs = [p.strip() for p in paragraphs if p.strip() not in repetitive_blocks]
    text = '\n\n'.join(clean_paragraphs)
    
    # 3. Remove números de página isolados
    text = re.sub(r'(?m)^\s*\d+\s*$', '', text)
    
    # 4. Transforma linhas em CAIXA ALTA (títulos) em headers Markdown (##)
    titulo = r'(?m)^\s*([A-ZÇÃÕÁÉÍÓÚÂÊÔ0-9 \.\-:\/]{4,150})\s*$'
    text = re.sub(titulo, r'\n\n## \1\n\n', text)
    
    # 5. Normaliza as quebras de linha e limpa as bordas
    return re.sub(r'\n{3,}', '\n\n', text).strip()