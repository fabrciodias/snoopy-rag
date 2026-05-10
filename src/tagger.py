import json
import os
from google import genai
from google.genai import types

def get_metadata(markdown_text):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(base_dir, 'credentials.json')
    
    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('api_key')
    except Exception as e:
        print(f"[ERRO FATAL] Problema ao ler credentials.json: {e}")
        return None
    
    client = genai.Client(api_key=api_key)
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
    """ + markdown_text[:5000]

    try:
        response = client.models.generate_content(
            model ='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",  
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"[ERRO NA API] A conexão com o Gemini falhou: {e}")
        return None

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_file = os.path.join(base_dir, 'data', 'markdown', 'teste_processado.md')
    
    if not os.path.exists(md_file):
        print("Arquivo .md não encontrado. O extractor.py precisa rodar primeiro.")
    else:
        with open(md_file, 'r', encoding='utf-8') as f:
            texto = f.read()
        print("Enviando para a nuvem\n")

        metadados = get_metadata(texto)

        if metadados:
            print("Registro do arquivo:\n")
            print(json.dumps(metadados, indent=4, ensure_ascii=False))
