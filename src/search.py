# 1. IMPORTAÇÕES 
import os 
import json
import sys
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client

# 2. CONFIGURAÇÕES GLOBAIS
load_dotenv()

# Silencia logs barulhentos das bibliotecas HTTP para não poluir o Node.js
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("google_genai.models").setLevel(logging.WARNING)

# 3. FUNÇÕES UTILITÁRIAS DE TELEMETRIA 
def ui_log(message):
    """Envia logs em tempo real (SSE) para o front-end via stderr"""
    print(f"UI_LOG::{message}", file=sys.stderr, flush=True)

# 4. MOTOR LÓGICO E ROTEAMENTO 
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
        print(f"[AVISO] Falha na decomposição, usando query original: {e}", file=sys.stderr)
        return [query]

# 5. PIPELINE DE BUSCA E SÍNTESE (RAG CORE)
def init_search(search_query, user_id, folder_id, gemini_api_key):
    # 5.1. Inicialização de Clientes
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

    if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, gemini_api_key]):
        print(json.dumps({"error": "Credenciais da nuvem ou do Gemini faltando no ambiente."}, ensure_ascii=False))
        return
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = genai.Client(api_key=gemini_api_key)
    
    # 5.2. Decomposição da Pergunta
    ui_log("Analisando estrutura da pergunta...")
    queries = decompose_query(search_query, client)
    all_results = []

    # 5.3. Varredura Vetorial no Supabase
    ui_log(f"Escaneando o acervo em busca de respostas...")
    for q in queries:
        try:
            response = client.models.embed_content(
                model='text-embedding-004',
                contents=q,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            query_vector = response.embeddings[0].values
            
            rpc_response = supabase.rpc('match_chunks', {
                'query_embedding': query_vector,
                'match_threshold': 0.4,
                'match_count': 5,
                'p_user_id': user_id,
                'p_folder_id': folder_id
            }).execute()

            for row in rpc_response.data:
                all_results.append({
                    "id": row['id'],
                    "text": row['content'],
                    "meta": {
                        "titulo_original": row['title'],
                        "autores": row.get('authors', []),
                        "ano_publicacao": row.get('publication_year', ''),
                        "arquivo_origem": "Drive/Supabase",
                        "secao": row['section'],
                        "link_drive": row['drive_link']
                    }
                })
        except Exception as e:
            print(f"Erro na busca vetorizada: {e}", file=sys.stderr)
    
    # 5.4. Deduplicação de Contextos (Remove trechos idênticos retornados por sub-buscas diferentes)
    unique_text = {}
    for res in all_results:
        clean_text = " ".join(res['text'].split()).lower()
        if clean_text not in unique_text:
            unique_text[clean_text] = res

    unique_results = list(unique_text.values())

    if not unique_results:
        ui_log("Nenhum contexto encontrado para essa pergunta.")
        print(json.dumps({"query": search_query, "answer": "Nenhum contexto encontrado", "sources": []}, ensure_ascii=False))
        return
        
    top_results = unique_results[:10]
   
    # 5.5. Formatação do Contexto para a LLM e Agrupamento de Referências
    context = ""
    unique_docs = {}
    
    for idx, res in enumerate(top_results):
        trecho_num = str(idx + 1)
        context += f"[TRECHO {trecho_num}]\n{res['text']}\n\n"
        title = res['meta'].get('titulo_original', 'Sem título')

        if title not in unique_docs:
            unique_docs[title] = {
                "titulo": title,
                "autores": res['meta'].get('autores', []),
                "ano": res['meta'].get('ano_publicacao', ''),
                "arquivo": res['meta'].get('arquivo_origem', 'Desconhecido'),
                "link": res['meta'].get('link_drive', 'Link indisponível'),
                "trechos": [trecho_num]
            }
        else:
            unique_docs[title]["trechos"].append(trecho_num)
            
    used_fonts = list(unique_docs.values())

    # 5.6. Geração da Síntese (O Dossiê Final)
    ui_log(f"Lendo referências e extraindo síntese...")

    prompt_rag = f"""
        Você é um assistente acadêmico de um grupo de pesquisa (Snoopy-RAG).
        Sua missão é gerar um dossiê sintético respondendo à pergunta do usuário, utilizando ESTRITAMENTE as informações dos trechos abaixo.
        
        REGRA DE AUDITORIA (CRÍTICA): 
        - Toda afirmação técnica DEVE ser seguida imediatamente por sua fonte no formato [TRECHO X].
        - Não agrupe citações no final do texto. Cite a cada frase ou conceito. Exemplo: "A regulação formativa altera o processo [TRECHO 1], exigindo adaptação do professor [TRECHO 2]."
        - Se a informação não estiver nos trechos, responda categoricamente: "Não encontrei informações nos documentos indexados para responder a esta pergunta."
        - NUNCA crie conclusões autorais ou deduções que não estejam explicitamente escritas nos trechos.
            
        PERGUNTA DO USUÁRIO: {search_query}
            
        CONTEXTOS RECUPERADOS (Use o número do TRECHO para as citações):
        {context}
        """
        
    try:
        llm_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_rag,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        texts_list = [{"num": str(i + 1), "text": res['text']} for i, res in enumerate(top_results)]
    
        final_output = {
            "query": search_query,
            "answer": llm_response.text,
            "sources": used_fonts,
            "chunks": texts_list
        }
        
        ui_log("Finalizando formatação da resposta...")
        # O Node.js está escutando o stdout para extrair este JSON
        print(json.dumps(final_output, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"Erro ao processar a síntese final: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}, ensure_ascii=False))

# 6. PONTO DE ENTRADA (CLI) 
if __name__ == '__main__':
    if len(sys.argv) < 5:
        print(json.dumps({"error": "Parâmetros insuficientes passados pelo Node.js."}, ensure_ascii=False))
        sys.exit(1)
        
    query_param = sys.argv[1]
    user_id_param = sys.argv[2]
    folder_id_param = sys.argv[3]
    gemini_api_key_param = sys.argv[4]

    init_search(query_param, user_id_param, folder_id_param, gemini_api_key_param)