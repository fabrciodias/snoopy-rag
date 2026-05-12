import os 
import re
import json
import chromadb 
from google import genai
from google.genai import types
from flashrank import Ranker, RerankRequest

def decompose_query(query, client):
    prompt = f"""
    Você é um roteador de buscas acadêmicas de alta precisão.
    Sua função é analisar a pergunta do usuário e quebrá-la em micro-buscas focadas e independentes.
    
    REGRA CRÍTICA DE AUTORIA: Se a pergunta citar múltiplos autores, obras ou conceitos, VOCÊ DEVE mapear qual conceito pertence a qual autor. 
    - Inclua o nome do autor APENAS na sub-busca correspondente à sua respectiva teoria. 
    - NÃO misture autores na mesma linha (ex: "AutorA AutorB conceito"), a menos que a pergunta peça explicitamente uma conexão ou comparação.
    - Crie linhas de busca independentes para cada núcleo conceitual.
    
    Exemplo de Roteamento Inteligente:
    - Pergunta: "O que [Autor A] diz sobre [Conceito X] e como [Autor B] aborda [Conceito Y]?"
    - Sub-buscas esperadas: 
      ["[Autor A] [Conceito X]", "[Autor B] [Conceito Y]", "conexão [Conceito X] e [Conceito Y]"]
    
    REGRA OBRIGATÓRIA: Retorne APENAS um array JSON de strings, sem formatação markdown ou texto extra.
    
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
        return json.loads(response.text)
    except Exception as e:
        print(f"[AVISO] Falha na decomposição, usando query original: {e}")
        return [query]

def init_search():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(base_dir, 'credentials.json')
    state_path = os.path.join(base_dir, 'data', 'drive_state.json')
    try:
        with open(cred_path, 'r', encoding='utf-8') as f:
            creds = json.load(f)
            api_key = creds.get('api_key')
            folder_id = creds.get('folder_id')
            folder_name = creds.get('folder_name', 'Acervo Particular')
    except Exception as e:
        print(f"[ERRO] Falha ao ler credentials.json: {e}")
        return
    if not folder_id:
        print("[ERRO] 'folder_id' não encontrado no credentials.json.")
        return

    file_count = 0
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
            file_count = sum(1 for v in state.values() if v.get('status') == 'processado')

    client = genai.Client(api_key=api_key)
    db_path = os.path.join(base_dir, 'data', 'chroma_db')
    chroma_client = chromadb.PersistentClient(path=db_path)
    safe_name = "pasta_" + re.sub(r'[^a-z0-9_]', '', folder_id.lower())
    collection = chroma_client.get_or_create_collection(name=safe_name)
    ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=os.path.join(base_dir, 'data', 'flashrank_cache'))
    
    print("="*50)
    print("SNOOPY-RAG: MOTOR DE BUSCA SEMÂNTICA ATIVADO")
    print("="*50)
    print("Carregando motor de Reranking (FlashRank)...")
    print(f"Documentos disponíveis: {file_count} arquivos(s) (Acervo: {folder_name}).")
    print("Digite 'sair' a qualquer momento para encerrar.\n")

    while True:
        search = input("Pesquisar:")
        if search.lower().strip() == 'sair':
            print("Saindo.")
            break
        if not search.strip():
            continue
        print("Analisando complexidade da pergunta...")

        queries = decompose_query(search, client)
        all_results = []
        for q in queries:
            try:
                response = client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=q
                )
                vector = response.embeddings[0].values
                results = collection.query(
                    query_embeddings=[vector],
                    n_results=5
                )

                for i in range(len(results['documents'][0])):
                    doc = results['documents'][0][i]
                    meta = results['metadados'][0][i]
                    all_results.append({
                        "id": i,
                        "text": __doc__,
                        "meta": meta
                    })
            except Exception as e:
                print(f"Erro na busca da micro-query '{q}': {e}")

        unique_results = {res['id']: res for res in all_results}.values()
        passages = [{"id": res['id'], "text": res['text'], "meta": res['meta']} for res in unique_results]

        if not passages:
            print("Nenhum contexto encontrado para essa pergunta.")
            continue

        rerank_request = RerankRequest(query=search, passages=passages)
        reranked_results = ranker.rerank(rerank_request)
        top_results = reranked_results[:10]

        context = ""
        used_fonts = set()
        for idx, res in enumerate(top_results):
            context += f"[TRECHO {idx+1}]\n{res['text']}\n\n"
            link = res['meta'].get('link_drive', 'Link indisponível')
            titulo = res['meta'].get('titulo_original', 'Sem título')
            arquivo = res['meta'].get('arquivo_origem', 'Desconhecido')
            secao = res['meta'].get('secao', 'Geral')
            used_fonts.add(f"Título: {titulo} | Arquivo: {arquivo} | Seção: {secao} | Link: {link}")
        print(f"Lendo {len(top_results)} referências e gerando resposta...")

        prompt_rag = f"""
            Você é um assistente acadêmico de um grupo de pesquisa.
            Responda à pergunta do usuário utilizando ESTRITAMENTE as informações fornecidas nos trechos de contexto abaixo.
            REGRA DE CITAÇÃO: Toda vez que você usar uma informação de um trecho, você deve obrigatoriamente colocar a referência logo após a frase. Exemplo: "A regulação é essencial para o ensino [TRECHO 2]."
            Se a resposta não estiver nos trechos, diga claramente: "Não encontrei informações suficientes nos documentos indexados para responder a esta pergunta."
            Não invente informações.
            
            PERGUNTA DO USUÁRIO: {search}
            
            CONTEXTOS RECUPERADOS:
            {context}
            """
        try:
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