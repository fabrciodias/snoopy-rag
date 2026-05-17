# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from collections import Counter

def to_markdown(raw_text):
    if not raw_text: return ""
    
    text = re.sub(r'\.{4,}', ' ', raw_text)
    paragraphs = text.split('\n\n')
    block_counts = Counter(p.strip() for p in paragraphs if len(p.strip()) > 15)
    repetitive_blocks = {p for p, count in block_counts.items() if count > 3}

    clean_paragraphs = [p.strip() for p in paragraphs if p.strip() not in repetitive_blocks]
    
    text = '\n\n'.join(clean_paragraphs)
    text = re.sub(r'(?m)^\s*\d+\s*$', '', text)
    titulo = r'(?m)^\s*([A-ZÇÃÕÁÉÍÓÚÂÊÔ0-9 \.\-:\/]{4,150})\s*$'
    text = re.sub(titulo, r'\n\n## \1\n\n', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()