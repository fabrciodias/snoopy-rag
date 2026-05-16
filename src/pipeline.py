# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import gc
import hashlib
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai
from google.genai import types
from extractor import extract_pdf_data
from cleaner import to_markdown
from tagger import get_metadata
from chunker import semantic_chunking

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
API_KEY = os.environ.get("API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
gemini_client = genai.Client(api_key=API_KEY)

def memory_process(file_path, file_id, user_id, folder_id, drive_link=""):
    try:
        print(f"\n[0/6] Gerando Hash de Segurança...")
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            doc_hash = hashlib.md5(file_bytes).hexdigest()

        existing_doc = supabase.table("documents").select("id").eq("folder_id", folder_id).eq("document_hash", doc_hash).execute()
        if len(existing_doc.data) > 0:
            print(f"[AVISO] Arquivo indêntico já existe no acervo (Hash: {doc_hash}). Processamento cancelado para este arquivo.")
            if os.path.exists(file_path):
                os.remove(file_path)
            return 
        
        print(f"\n[1/6] Extraindo texto: {file_path}")
        pdf_meta, raw_text = extract_pdf_data(file_path)

        if not raw_text:
            raise Exception("PDF vazio ou corrompido.")
        
        print("[2/6] Limpando ruídos e formatando Markdown...")
        clean_md = to_markdown(raw_text)

        print("[3/6] LLM Tagger: Extraindo Metadados Semânticos...")
        semantic_meta = get_metadata(clean_md, gemini_client)
        title = semantic_meta.get("titulo_original", os.path.basename(file_path))

        print("[4/6] Registrando Documento no Supabase...")
        doc_response = supabase.table("documents").insert({
            "user_id": user_id,
            "folder_id": folder_id,
            "document_hash": doc_hash,
            "title": title,
            "drive_link": drive_link,
            "drive_file_id": file_id
        }).execute()

        document_id = doc_response.data[0]['id']

        print("[5/6] Dividindo o texto (Chunking)...")
        chunks = semantic_chunking(clean_md, {})

        print(f"[6/6] Vetorizando {len(chunks)} chunks e subindo para Nuvem...")
        batch_size = 5
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c['text'] for c in batch]

            response = gemini_client.models.embed_content(
                model='gemini-embedding-001',
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=768)            
            )
            supabase_payload = []
            for j, emb in enumerate(response.embeddings):
                supabase_payload.append({
                    "document_id": document_id,
                    "folder_id": folder_id,
                    "user_id": user_id,
                    "content": batch[j]['text'],
                    "section": batch[j]['metadata'].get('secao', 'Geral'),
                    "embedding": emb.values
                })
            supabase.table("chunks").insert(supabase_payload).execute()
            print(f"-> Lote {i+1} a {min(i+batch_size, len(chunks))} salvo no Supabase.")
        
        print("\n[SUCESSO] Pipeline concluído! Limpando memória e apagando PDF...")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        del raw_text, clean_md, chunks, supabase_payload
        gc.collect()
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha no processamento: {e}")

if __name__ == "__main__":
    pdf_source = "data/raw_pdfs/(A2)-Coévaluation entre pairs apprenants comme échafaudage de la régulation du processus de l'apprentissage  e-JIREF.pdf"
    supabase_id = "7d373e2e-2efb-4715-b7db-25a15e21bc93"
    supabase_folder = "f7faf7d9-ec80-46c6-9572-174865bf1e62"

    print("Iniciando teste...")
    memory_process(pdf_source, "file_id_123", supabase_id, supabase_folder)
