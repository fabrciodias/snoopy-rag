# Snoopy-RAG: Sistema de Busca Semântica Documental

O **Snoopy-RAG** é uma infraestrutura local de Recuperação Aumentada por Geração (RAG) desenvolvida para indexar e consultar coleções de artigos, teses e livros. O projeto foca no rigor acadêmico, garante consultas rápidas e rastreia estritamente as informações geradas através de citações diretas.

## 1. Arquitetura Efêmera e Otimização

O sistema roda sob restrições severas de hardware, validado em um servidor de 2011 (4GB de RAM DDR3, sem GPU, Ubuntu 22.04).

Para evitar travamentos por falta de memória (OOM), o Snoopy-RAG processa dados em *streaming* e executa cada etapa do pipeline em subprocessos isolados. Na versão atual, a arquitetura tornou-se **efêmera e isolada**:

* **Efêmera (Limpeza do Disco):** O sistema deleta os PDFs originais do disco imediatamente após a extração do conhecimento (Markdown), poupando armazenamento físico.
* **Isolada (Folder-Tenancy):** O banco de dados cria coleções independentes para cada pasta do Drive, permitindo gerenciar múltiplos acervos sem misturar contextos.

## 2. Pipeline de Processamento (Módulos)

O sistema opera de forma linear com scripts de responsabilidade única:

* **`drive_sync.py`**: Gerencia a coleta. Sincroniza arquivos do Google Drive e controla o estado local (`drive_state.json`), detectando atualizações de versão automaticamente.
* **`extractor.py` & `cleaner.py**`: Extraem o texto do PDF, normalizam o conteúdo em Markdown semântico usando heurísticas e excluem o arquivo original do HD.
* **`tagger.py`**: Extrai metadados precisos com IA (Gemini). Atrela os dados ao ID imutável do Drive, o que previne duplicação de vetores no banco de dados.
* **`chunker.py`**: Fatie o texto semanticamente com base nas seções. Grava os resultados em streaming (`.jsonl`).
* **`embedder.py`**: Cria o banco vetorial isolado para a pasta específica no ChromaDB. Consulta o cache local e vetoriza apenas os blocos inéditos.
* **`search.py`**: Motor de busca e API. Recebe a pergunta via linha de comando, isola os logs de processamento e devolve uma resposta estruturada e limpa em formato JSON. Usa decomposição de perguntas e re-ranqueamento com FlashRank.
* **`watcher.py`**: O orquestrador. Executa o pipeline de ingestão de ponta a ponta.

## 3. Rastreabilidade e Citações

Para impedir alucinações, o sistema usa engenharia de prompt restritiva. Toda afirmação gerada na resposta inclui obrigatoriamente a referência direta ao bloco de texto correspondente (exemplo: `[TRECHO 3]`). A IA admite imediatamente a ausência de informações caso a resposta não exista nos documentos indexados.

## 4. Instalação e Configuração

*(Nota: O script criará o diretório `/data` automaticamente na primeira execução para armazenar as bases).*

### Passo 1: Clonar e Preparar o Ambiente

No terminal, clone o projeto e crie o ambiente virtual:

```
git clone https://github.com/fabrciodias/snoopy-rag.git
cd snoopy-rag

```

**Criando e ativando o ambiente virtual:**

* **Linux / macOS:**

```
python3 -m venv .venv
source .venv/bin/activate

```

* **Windows (Prompt de Comando ou PowerShell):**

```
python -m venv .venv
.\.venv\Scripts\activate

```

*(Nota: No PowerShell, se houver erro de permissão, rode `Set-ExecutionPolicy Unrestricted -Scope CurrentUser`, confirme e tente novamente).*

### Passo 2: Instalar Dependências

Com o ambiente ativo `(.venv)`, instale os pacotes:

```
pip install -r requirements.txt

```

### Passo 3: Configuração das APIs (Google)

O ecossistema depende das ferramentas do Google:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/), crie um projeto e gere uma **Conta de Serviço**.
2. Crie uma chave JSON para esta conta, faça o download, renomeie para `credentials.json` e coloque na raiz do projeto.
3. Gere uma chave de API no [Google AI Studio](https://aistudio.google.com/).
4. Abra o `credentials.json` e adicione manualmente `api_key`, `folder_id` e `folder_name` no topo do arquivo:

```
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

1. Abra a pasta do seu acervo no Google Drive.
2. Compartilhe a pasta como **Leitor** com o e-mail do seu bot (o `client_email` do JSON).
3. Copie o ID da pasta na URL (exemplo: `drive.google.com/drive/folders/ID_DA_PASTA`) e cole no seu `credentials.json`.

## 5. Uso

Sempre execute os comandos com o ambiente virtual ativo.

**Para processar PDFs, atualizar a base e alimentar o banco vetorial:**

```
python src/watcher.py

```

**Para consultar o acervo (O script devolve a resposta em formato JSON):**

```
python src/search.py "O que diz o autor sobre este conceito?"

```

## 6. Código Aberto e Contribuições

Este projeto possui arquitetura transparente e pragmática. Clone, modifique e adapte livremente. Crie *forks*, ajuste heurísticas ou otimize o pipeline. Pull Requests são bem-vindos.