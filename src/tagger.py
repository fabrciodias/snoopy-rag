# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from google.genai import types

def get_metadata(markdown_text, client):
    prompt = """
    Você é um bibliotecário acadêmico especialista em extração de metadados.
    Leia o trecho inicial deste documento acadêmico e extraia as seguintes informações.
    
    REGRAS OBRIGATÓRIAS:
    - Retorne APENAS um JSON válido.
    - Se uma informação não for encontrada no texto, retorne null.
    
    ESTRUTURA DO JSON:
    - titulo_original (string)
    - autores (lista de strings)
    - ano_publicacao (string, apenas o ano)
    - tipo_documental (string, ex: Tese, Dissertação, Artigo, etc)
    - idioma (string, ex: pt-br, en, fr)
    - palavras_chave (lista de strings)

    TEXTO DO DOCUMENTO:
    """ + markdown_text[:4000]

    try:
        response = client.models.generate_content(
            model ='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1  
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"[ERRO LLM] Erro ao extrair metadados: {e}")
        return {}