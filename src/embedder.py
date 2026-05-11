import os 
import json
import chromadb
import time
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
    chunks_path = os.path.join(base_dir, 'data', 'chunks_teste.json')

    if not os.path.exists(chunks_path):
        print("[ERRO] Arquivo chunks_teste.json não encontrado.")
        return
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"Iniciando a vetorização de {len(chunks)} chunks com o Gemini...")

    documents = []
    metadatas = []
    ids = []
    embeddings = []
    batch_size = 5

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texto = [c['text'] for c in batch]
        try:
            response = client.models.embed_content(
                model='gemini-embedding-001',
                contents=texto
            )
            for j, emb in enumerate(response.embeddings):
                idx = i + j
                documents.append(batch[j]['text'])
                metadatas.append(batch[j]['metadata'])
                ids.append(f"{batch[j]['metadata'].get('tipo_documental', 'Doc')}_{idx}")
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