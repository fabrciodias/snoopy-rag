import os 
import json
import chromadb 
from google import genai
from google.genai import types

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
            response_emb = client.models.embed_content(
                model='gemini-embedding-001',
                contents=search
            )
            vetor_search = response_emb.embeddings[0].values
            result = collection.query(
                query_embeddings=[vetor_search],
                n_results=3
            )

            context = ""
            used_fonts = []
            for i in range(len(result['documents'][0])):
                text = result['documents'][0][i]
                metadata = result['metadatas'][0][i]
                context += f"TRECHO {i+1} \n{text}\n"
                font = f"Título: {metadata.get('titulo_original')} | Seção: {metadata.get('secao')} | Link: {metadata.get('link_drive')}"
                
                if font not in used_fonts:
                    used_fonts.append(font)
            print("Lendo referências e gerando resposta (Gemini Flash)...")

            prompt_rag = f"""
            Você é um assistente acadêmico de um grupo de pesquisa chamado GEPAFOR.
            Responda à pergunta do usuário utilizando ESTRITAMENTE as informações fornecidas nos trechos de contexto abaixo.
            Se a resposta não estiver nos trechos, diga claramente: "Não encontrei informações suficientes nos documentos indexados para responder a esta pergunta."
            Não invente informações.
            
            PERGUNTA DO USUÁRIO: {search}
            
            CONTEXTOS RECUPERADOS:
            {context}
            """
            llm_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_rag,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                )
            )
            print("\n" + "="*50)
            print("RESPOSTA DO SNOOPY-RAG")
            print("="*50)
            print(llm_response.text)
            print("\n" + "-"*50)
            print("FONTES CONSULTADAS:")
            for f in used_fonts:
                print(f"- {f}")
            print("-" * 50)

        except Exception as e:
            print(f"Erro ao processar a busca: {e}")
        
if __name__ == '__main__':
    init_search()