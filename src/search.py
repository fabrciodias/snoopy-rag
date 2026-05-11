import os 
import json
import chromadb 
from google import genai

def init_search():
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
    collection = chroma_client.get_collection(name="docs")

    print("==================================================")
    print("SNOOPY-RAG: MOTOR DE BUSCA SEMÂNTICA ATIVADO")
    print("==================================================")
    print(f"Documentos no radar: {collection.count()} blocos.")
    print("Digite 'sair' a qualquer momento para encerrar.\n")

    while True:
        search = input("Pesquisar:")
        if search.lower().strip() == 'sair':
            print("Saindo.")
            break
        if not search.strip():
            continue
        print("Pesquisando...")

        try:
            response = client.models.embed_content(
                model='gemini-embedding-001',
                contents=search
            )
            vetor_search = response.embeddings[0].values
            result = collection.query(
                query_embeddings=[vetor_search],
                n_results=3
            )

            print("\nPRINCIPAIS RESULTADOS DA BUSCA:")
            print("-" * 50)

            for i in range(len(result['documents'][0])):
                text = result['documents'][0][i]
                metadata = result['metadatas'][0][i]
                distance = result['distances'][0][i]

                print(f"RESULTADO {i+1} (Distância: {distance:.4f})")
                print(f"Título: {metadata.get('titulo_original')}")
                print(f"Seção: {metadata.get('secao')}")
                print(f"Link Drive: {metadata.get('link_drive')}")
                print("\nTRECHO ENCONTRADO:")
                print(text)
                print("-" * 50)

        except Exception as e:
            print(f"Erro ao processar a busca: {e}")
        
if __name__ == '__main__':
    init_search()