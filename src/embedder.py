import os 
import json
import chromadb
import time
import hashlib
from google import genai

def run_embedder():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(base_dir, 'credentials.json')
    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('api_key')
    except Exception as e:
        print(f"[ERRO] Falha ao ler credentials.json: {e}")
        return
    
    client = genai.Client(api_key=api_key)
    db_path = os.path.join(base_dir, 'data', 'chroma_db')
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="docs")
    chunks_path = os.path.join(base_dir, 'data', 'chunks.json')

    if not os.path.exists(chunks_path):
        print("[ERRO] Arquivo chunks.json não encontrado.")
        return
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    print("\n[CACHE] Verificando blocos já existentes...")
    to_process = []

    for chunk in chunks:
        text_chunk = chunk['text']
        metadata_chunk = chunk['metadata']
        seal = f"{metadata_chunk.get('hash_md5', 'nohash')}_{text_chunk}"
        chunk_id = hashlib.md5(seal.encode('utf-8')).hexdigest()
        result = collection.get(ids=[chunk_id])

        if len(result['ids']) == 0:
            chunk['hash_id'] = chunk_id
            to_process.append(chunk)
    print(f"[CACHE] Dos {len(chunks)} blocos, {len(to_process)} são novos e serão vetorizados.")

    if not to_process:
        print("Todas as chunks já foram processadas. Nenhuma requisição gasta. Encerrando.")
        return
    print(f"\nIniciando a vetorização de {len(chunks)} chunks com o Gemini...")

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

            print(f"Lote processado: Chunks {i+1} até {min(i+batch_size, len(chunks))} vetorizadas.")
            time.sleep(4)

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