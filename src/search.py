import os 
import json
import chromadb 
import time
from google import genai
from google.genai import types
from flashrank import Ranker, RerankRequest

def decompose_query(query, client):
    prompt = f"""
    Você é um roteador de buscas acadêmicas. Analise a pergunta do usuário. 
    Se for uma pergunta complexa com vários temas, quebre-a em sub-perguntas simples e diretas, focadas em um único conceito cada.
    Se a pergunta for simples e direta, retorne-a como o único item da lista.
    
    REGRA OBRIGATÓRIA: Retorne APENAS um array JSON contendo as strings das perguntas.
    
    Pergunta do Usuário: {query}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        sub_queries = json.loads(response.text)
        if isinstance(sub_queries, list):
            return sub_queries
        return [query]
    except Exception as e:
        print(f"[AVISO] Falha na decomposição, usando query original: {e}")
        return [query]

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

    print("Carregando motor de Reranking (FlashRank)...")
    models_dir = os.path.join(base_dir, 'data', 'models')
    os.makedirs(models_dir, exist_ok=True)
    ranker = Ranker(cache_dir=models_dir)

    print(f"Documentos no radar: {collection.count()} blocos.")
    print("Digite 'sair' a qualquer momento para encerrar.\n")

    while True:
        search = input("Pesquisar:")
        if search.lower().strip() == 'sair':
            print("Saindo.")
            break
        if not search.strip():
            continue
        print("Analisando complexidade da pergunta...")
        sub_queries = decompose_query(search, client)

        if len(sub_queries) > 1:
            print(f"Pergunta decomposta em {len(sub_queries)} micro-buscas:")
            for sq in sub_queries:
                print(f"-{sq}")
        else:
            print("Pergunta direta. Fluxo normal.")
        unique_chunks = {}
        used_fonts = []

        try:
            for sq in sub_queries:
                response_emb = client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=sq
                )

                vetor_search = response_emb.embeddings[0].values
                result = collection.query(
                    query_embeddings=[vetor_search],
                    n_results=15
                )

                passages = []
                for i in range(len(result['documents'][0])):
                    raw_text = result['documents'][0][i]
                    if not raw_text or len(str(raw_text).strip()) < 10:
                        continue

                    passages.append({
                        "id": i,
                        "text": str(raw_text),
                        "meta": result['metadatas'][0][i]
                    })

                re_rank = RerankRequest(query=search, passages=passages)
                re_results = ranker.rerank(re_rank)
                results = re_results[:3]
               
                for i, doc in enumerate(results):
                    text_content = doc['text']
                    metadata = doc['meta']
                    if text_content not in unique_chunks:
                        unique_chunks[text_content] = metadata

            context = ""
            counter = 1 
            for text, meta in unique_chunks.items():
                context += f"TRECHO {counter} \n{text}\n\n"
                counter += 1     

                font = f"Título: {meta.get('titulo_original')} | Arquivo: {meta.get('arquivo_origem')} | Seção: {meta.get('secao')} | Link: {meta.get('link_drive')}"          
                if font not in used_fonts:
                    used_fonts.append(font)

            print(f"\Lendo {len(unique_chunks)} referências e gerando resposta (Gemini Flash)...")
            

            prompt_rag = f"""
            Você é um assistente acadêmico de um grupo de pesquisa.
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