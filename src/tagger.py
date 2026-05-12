import json
import os
from datetime import datetime
from google import genai
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

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, 'data', 'documents')
    cred_path = os.path.join(base_dir, 'credentials.json')
    state_path = os.path.join(base_dir, 'data', 'drive_state.json')
    
    try:
        with open(cred_path, 'r') as f:
            api_key = json.load(f).get('api_key')
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[ERRO FATAL] credenciais: {e}")
        exit()

    state_data = {}
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
    print(f"Iniciando cofre de Metadados em: {docs_dir}\n")

    for folder_name in os.listdir(docs_dir):
        doc_folder = os.path.join(docs_dir, folder_name)
        if not os.path.isdir(doc_folder):
            continue
        md_path = os.path.join(doc_folder, 'semantic.md')
        meta_path = os.path.join(doc_folder, 'metadata.json')

        if os.path.exists(meta_path):
            print(f"Pulando: Metadados já existem para '{folder_name}'")
            continue
        if not os.path.exists(md_path):
            print(f"Aviso: semantic.md não encontrado em '{folder_name}'")
            continue
        print(f"Analisando: {folder_name}...")

        with open(md_path, 'r', encoding='utf-8') as f:
            text = f.read()
        semantic_data = get_metadata(text, client)

        if not semantic_data:
            print("Falha na esxtração. Pulando...")
            continue

        link_drive = "Link não encontrado"
        origin_file = folder_name + ".pdf"
        doc_id = folder_name

        for file_id, info in state_data.items():
            filename = info.get('name', '')
            clean_name = filename[:-4].strip() if filename.lower().endswith('.pdf') else filename

            if clean_name == folder_name:
                link_drive = info.get('webViewLink', 'Link não encontrado')
                origin_file = filename
                doc_id = file_id
                break

        final_metadata = {
           "id_documento": doc_id,
            "arquivo_origem": origin_file,
            "data_ingestao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "link_drive": link_drive,
            "status": "indexado",
            **semantic_data 
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(final_metadata, f, indent=4, ensure_ascii=False)
        print("metadata.json gerado e arquivado.")
    print("\nProcesso de registro finalizado.")