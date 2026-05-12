import os 
import json
import chromadb
import time
import re
import hashlib
from google import genai

def run_embedder():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(base_dir, 'credentials.json')
    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('api_key')
            folder_id = creds.get('folder_id')
    except Exception as e:
        print(f"[ERRO] Falha ao ler credentials.json: {e}")
        return
    if not folder_id:
        print("[ERRO] 'folder_id' não encontrado no credentials.json")
        return
    
    client = genai.Client(api_key=api_key)
    db_path = os.path.join(base_dir, 'data', 'chroma_db')
    chroma_client = chromadb.PersistentClient(path=db_path)

    safe_name = "pasta_" + re.sub(f'[^a-z0-9_]', '', folder_id.lower())
    collection = chroma_client.get_or_create_collection(name=safe_name)
    chunks_path = os.path.join(base_dir, 'data', 'chunks.jsonl')

    if not os.path.exists(chunks_path):
        print("[ERRO] Arquivo chunks.jsonl não encontrado.")
        return
    print("\n[CACHE] Verificando blocos já existentes (leitura em streaming)...")
    to_process = []
    total_chunks = 0

    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            chunk = json.loads(line)
            total_chunks += 1
            chunk_hash = chunk.get('hash_id')

            if not chunk_hash:
                text_to_hash = chunk['text'] + chunk['metadata'].get('id_documento', '')
                chunk_hash = hashlib.md5(text_to_hash.encode('utf-8')).hexdigest()
                chunk['hash_id'] = chunk_hash

            result = collection.get(ids=[chunk_hash])
            if not result['ids']:
                to_process.append(chunk)
    print(f"[CACHE] Dos {total_chunks} blocos, {len(to_process)} são novos e serão vetorizados.")

    if not to_process:
        print("Todas as chunks já foram processadas. Nenhuma nova requisição. Encerrando.")
        return
    print(f"\nIniciando a vetorização de {len(to_process)} chunks com o Gemini...")

    documents = []
    metadatas = []
    ids = []
    embeddings = []
    batch_size = 5

    for i in range(0, len(to_process), batch_size):
        batch = to_process[i : i + batch_size]
        texto = [c['text'] for c in batch]
        
        try:
            response = client.models.embed_content(
                model='gemini-embedding-001',
                contents=texto
            )
            for j, emb in enumerate(response.embeddings):
                text_chunk = batch[j]['text']
                metadata_chunk = batch[j]['metadata']
                chunk_id = batch[j]['hash_id']

                documents.append(text_chunk)
                metadatas.append(metadata_chunk)
                ids.append(chunk_id)
                embeddings.append(emb.values)

            print(f"Lote processado: Chunks {i+1} até {min(i+batch_size, len(to_process))} vetorizadas.")
            time.sleep(1)

        except Exception as e:
            print(f"Erro no lote {i}: {e}")
            time.sleep(10)

    if documents:
        print("\nSalvando as coordenadas no disco (ChromaDB)...")
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        print(f"Sucesso! Banco vetorial atualizado em: {db_path}")
        print(f"Total de blocos pesquisáveis na coleção: {collection.count()}")

if __name__ == '__main__':
    run_embedder()