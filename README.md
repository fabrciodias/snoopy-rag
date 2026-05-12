# Snoopy-RAG: Sistema de Busca Semântica Documental

O **Snoopy-RAG** é uma infraestrutura local de Recuperação Aumentada por Geração (RAG) desenvolvida para indexar e consultar coleções de artigos, teses e livros. O foco do projeto é o rigor acadêmico, garantindo consultas rápidas e a rastreabilidade estrita das informações geradas por meio de citações.

## 1. Arquitetura e Otimização de Hardware

O sistema foi desenvolvido sob restrições severas de hardware, sendo validado em um equipamento de 2011 (4GB de RAM DDR3, sem placa de vídeo dedicada, ambiente Ubuntu 22.04). 

Para evitar o esgotamento de memória (Out of Memory - OOM), a arquitetura do projeto é orientada a disco em vez de RAM. O processamento de dados ocorre via *streaming* (leitura e gravação linha a linha em arquivos `.jsonl`), e o pipeline de ingestão é executado em subprocessos isolados. Isso garante que a memória seja completamente liberada ao final de cada etapa do processamento documental.

## 2. Pipeline de Processamento (Módulos)

O sistema opera de forma linear, com scripts de responsabilidade única:

* **`drive_sync.py`:** Módulo de coleta. Realiza a sincronização autônoma e incremental com o Google Drive via Conta de Serviço, baixando apenas os PDFs não mapeados localmente.
* **`extractor.py` & `cleaner.py`:** Módulos de formatação. Extraem o texto bruto dos PDFs e utilizam heurísticas determinísticas para remover ruídos (paginação, cabeçalhos redundantes), gerando um documento em Markdown semântico.
* **`tagger.py`:** Módulo de indexação. Utiliza LLM (temperatura 0.1) para extrair metadados precisos (título, autores, ano) e gera um Hash MD5 único para o documento base.
* **`chunker.py`:** Realiza o fatiamento (chunking) semântico baseado na estrutura de seções do texto, preservando a coerência conceitual. Salva os blocos em formato de *streaming* (`.jsonl`).
* **`embedder.py`:** Módulo de vetorização. Implementa um **Cache Vetorial por Hash** local. Consulta o banco ChromaDB para verificar blocos existentes e consome a cota de API exclusivamente para vetorizar conteúdos inéditos.
* **`search.py`:** Motor de recuperação e geração. Fragmenta a pergunta original do usuário via *Decomposição Multi-Query Ancorada* para evitar desvios semânticos (*semantic drift*). Realiza o re-ranqueamento dos blocos com **FlashRank** e estrutura o contexto final para o LLM.
* **`watcher.py`:** O orquestrador. Executa o pipeline de ingestão sequencialmente e de forma isolada, registrando logs em tempo real do processamento.

## 3. Rastreabilidade e Citações

Para mitigar o problema de alucinação em modelos generativos, o sistema adota engenharia de prompt restritiva. Toda afirmação ou conceito gerado na resposta final inclui obrigatoriamente a referência direta ao bloco de texto correspondente (exemplo: `[TRECHO 3]`). O modelo é explicitamente instruído a admitir a ausência de informações caso a resposta não esteja nos documentos vetorizados.

## 4. Instalação e Configuração

*(Nota: A pasta `/data`, que armazena os PDFs, banco vetorial e chunks, não está no repositório. O próprio sistema criará essa estrutura dinamicamente na primeira execução).*

**Passo 1: Clonar o Repositório e Preparar o Ambiente**
```bash
git clone [https://github.com/fabrciodias/snoopy-rag.git](https://github.com/fabrciodias/snoopy-rag.git)
cd snoopy-rag
python3 -m venv .venv
source .venv/bin/activate
```

**Passo 2: Instalar Dependências**
```
pip install -r requirements.txt
```
*(Principais bibliotecas: `PyMuPDF`, `google-genai`, `chromadb`, `flashrank`, `google-api-python-client`)*.

**Passo 3: Configuração de Credenciais e Infraestrutura Google**

O sistema exige acesso a duas APIs do Google: a do Gemini (para IA) e a do Google Cloud (para ler o Drive autônomamente).

1. Gere uma API Key do Gemini no **Google AI Studio**.
2. Acesse o **Google Cloud Console**, crie um projeto e gere uma **Conta de Serviço (Service Account)**. Isso criará um "bot" com um e-mail próprio. Crie uma chave para essa conta no formato JSON e faça o download.
3. Na raiz do projeto Snoopy-RAG, renomeie o arquivo baixado para `credentials.json`.
4. Abra o `credentials.json` e adicione a sua chave do Gemini logo no início do arquivo, neste formato:
```json
{
  "api_key": "SUA_CHAVE_DO_GEMINI_AQUI",
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "seu-bot@seu-projeto.iam.gserviceaccount.com",
  ...
}
```

**Passo 4: Preparando o Google Drive**

1. Vá até a pasta do seu Google Drive onde os PDFs estão guardados.
2. Clique em Compartilhar e convide o e-mail do seu bot (o `client_email` gerado no passo anterior). Dê permissão de **Leitor** (Viewer).
3. Copie o ID da pasta (Exemplo: `https://drive.google.com/drive/folders/ID_DA_SUA_PASTA_DO_DRIVE?hl=pt-br`).
4. Abra o arquivo `src/drive_sync.py` e substitua o valor da variável `FOLDER_ID` pelo seu ID copiado.

## 5. Utilização

Com o ambiente e credenciais configurados, a utilização se divide em dois comandos:

**Para sincronizar o Drive e atualizar a base de conhecimento:**

```
./.venv/bin/python3 src/watcher.py
```

**Para iniciar o motor de buscas:**

```
./.venv/bin/python3 src/search.py
```

## 6. Código Aberto e Contribuições

Este é um projeto *open-source* com arquitetura documentada para facilitar modificações. O código pode ser clonado e adaptado livremente. Sinta-se à vontade para realizar *forks*, alterar a estrutura dos prompts, customizar heurísticas de limpeza no `cleaner.py` ou adicionar suporte a novos formatos de arquivo. Pull Requests com otimizações são bem-vindos.
