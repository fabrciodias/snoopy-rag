# Snoopy-RAG: Sistema de Busca Semântica Documental

O **Snoopy-RAG** é uma infraestrutura local de Recuperação Aumentada por Geração (RAG) desenvolvida para indexar e consultar coleções de artigos, teses e livros. O projeto foca no rigor acadêmico, garante consultas rápidas e rastreia estritamente as informações geradas através de citações diretas.

## 1. Arquitetura Híbrida e Otimização

O sistema roda sob restrições severas de hardware, validado em um servidor de 2011 (4GB de RAM DDR3, sem GPU, Ubuntu 22.04). A arquitetura foi dividida em módulos desacoplados para maximizar a eficiência e evitar travamentos por falta de memória (OOM):

* **Motor Semântico (Python):** Processa dados em *streaming* e atua de forma **efêmera**. Deleta os PDFs originais do disco após a extração e encerra seus processos imediatamente após cada resposta.
* **Isolamento (Folder-Tenancy):** O banco vetorial cria instâncias independentes para cada pasta do Google Drive, impedindo a contaminação de contexto entre acervos distintos.
* **Middleware (Node.js):** Atua como roteador seguro entre o navegador e o motor Python. Implementa um **cache semântico** baseado em hash MD5 da pergunta, anulando a latência e o custo de requisições repetidas na API.
* **Interface (Minimalismo Investigativo):** Front-end focado estritamente na leitura acadêmica, isolando a síntese gerada das provas documentais extraídas.

## 2. Pipeline de Processamento (Módulos)

O sistema opera de forma linear com arquivos de responsabilidade única:

* **`drive_sync.py`**: Gerencia a coleta. Sincroniza arquivos do Drive e controla o estado local (`drive_state.json`).
* **`extractor.py` & `cleaner.py`**: Extraem o texto do PDF, normalizam em Markdown semântico e excluem o arquivo original do HD.
* **`tagger.py`**: Extrai metadados precisos com IA (Gemini).
* **`chunker.py`**: Fatia o texto semanticamente com base nas seções. Grava os resultados em streaming (`.jsonl`).
* **`embedder.py`**: Cria o banco vetorial isolado para a pasta específica no ChromaDB.
* **`search.py`**: Motor de busca executado como subprocesso. Isola logs no `stderr` e devolve um JSON contendo a resposta gerada e os metadados das fontes.
* **`watcher.py`**: O orquestrador da ingestão documental de ponta a ponta.
* **`server.js`**: Servidor Express que recebe requisições web, aciona o cache ou o `search.py` e serve o Front-end.
* **`/ui`**: Diretório contendo a interface web em Vanilla HTML/CSS/JS.
* ## Estrutura do Projeto

```text
snoopy-rag/
├── src/
├── ui/
├── data/
├── chroma_db/
├── credentials.json
└── ...
```

## 3. Rastreabilidade e Citações

Para impedir alucinações, o sistema usa engenharia de prompt restritiva. Toda afirmação gerada inclui obrigatoriamente a referência direta ao bloco de texto correspondente (exemplo: `[TRECHO 3]`). 

O mapeamento das fontes é **exato (1:1)**. O sistema não desduplica documentos, garantindo que cada trecho referenciado na resposta possua um card correspondente no painel de evidências da interface web, com link direto à página/seção correta do arquivo original no Google Drive.

## 4. Instalação e Configuração

*(Nota: O script criará o diretório `/data` automaticamente na primeira execução).*

### Pré-requisitos
* Python 3.10+
* Node.js v20+

### Passo 1: Clonar e Preparar o Ambiente

```bash
git clone https://github.com/fabrciodias/snoopy-rag.git
cd snoopy-rag

```

**Criando e ativando o ambiente virtual (Python):**

* **Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate

```

* **Windows:**

```bash
python -m venv .venv
.\.venv\Scripts\activate

```

### Passo 2: Instalar Dependências

Com o ambiente Python ativo `(.venv)`, instale as bibliotecas do motor semântico:

```bash
pip install -r requirements.txt

```

No escopo global da pasta, instale a biblioteca do middleware Node.js:

```bash
npm install express

```

### Passo 3: Configuração das APIs (Google)

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/), crie um projeto e gere uma **Conta de Serviço**.
2. Crie uma chave JSON para esta conta, faça o download, renomeie para `credentials.json` e coloque na raiz do projeto.
3. Gere uma chave de API no [Google AI Studio](https://aistudio.google.com/).
4. Abra o `credentials.json` e adicione manualmente `api_key`, `folder_id` e `folder_name` no topo do arquivo:

```json
{
  "api_key": "SUA_CHAVE_GEMINI_AQUI",
  "folder_id": "ID_DA_SUA_PASTA_DO_DRIVE_AQUI",
  "folder_name": "NOME_DO_SEU_ACERVO_AQUI",
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "seu-bot@seu-projeto.iam.gserviceaccount.com"
}

```

### Passo 4: Permissões no Google Drive

1. Compartilhe a pasta do seu acervo no Google Drive como **Leitor** com o e-mail do seu bot (o `client_email` do JSON).
2. Copie o ID da pasta na URL e cole no seu `credentials.json`.

## 5. Uso

**Para processar PDFs, atualizar a base e alimentar o banco vetorial:**
Execute no ambiente virtual Python:

```bash
python src/watcher.py

```

**Para iniciar o servidor e acessar a interface de consulta:**
Execute no diretório raiz:

```bash
node server.js

```

Acesse `http://localhost:3333` em seu navegador.

## 6. Código Aberto e Contribuições

Este projeto possui arquitetura transparente e pragmática. Clone, modifique e adapte livremente. Crie *forks*, ajuste heurísticas ou otimize o pipeline. Pull Requests são bem-vindos.
