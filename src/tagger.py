import json
import sys
from google.genai import types

def get_metadata(markdown_text, client):
    prompt = f"""
    Você é um bibliotecário acadêmico especialista em extração de metadados.
    Leia o trecho inicial deste documento acadêmico e extraia as seguintes informações.
    
    REGRAS OBRIGATÓRIAS:
    - Retorne APENAS um JSON válido.
    - Se uma informação não for encontrada no texto, retorne null.
    
    ESTRUTURA DO JSON ESPERADA:
    {{
        "titulo_original": "string",
        "autores": ["lista", "de", "strings"],
        "ano_publicacao": "string (apenas o ano)",
        "tipo_documental": "string (ex: Tese, Dissertação, Artigo)",
        "idioma": "string (ex: pt-br, en, fr)",
        "palavras_chave": ["lista", "de", "strings"]
    }}

    TEXTO DO DOCUMENTO:
    {markdown_text[:4000]}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        # Redireciona o erro para o stderr para não poluir o pipeline
        print(f"[ERRO LLM TAGGER] Falha ao extrair metadados: {e}", file=sys.stderr)
        return {}