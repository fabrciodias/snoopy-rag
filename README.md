# Snoopy-RAG: Sistema de Busca Semântica Documental

O **Snoopy-RAG** é uma infraestrutura local de Recuperação Aumentada por Geração (RAG) desenvolvida para indexar e consultar coleções de artigos, teses e livros. O foco do projeto é o rigor acadêmico, garantindo consultas rápidas e a rastreabilidade estrita das informações geradas por meio de citações.

## 1. Arquitetura e Otimização de Hardware

O sistema foi desenvolvido sob restrições severas de hardware, sendo validado em um equipamento de 2011 (4GB de RAM DDR3, sem placa de vídeo dedicada, ambiente Ubuntu 22.04). 

Para evitar o esgotamento de memória (Out of Memory - OOM), a arquitetura do projeto é orientada a disco em vez de RAM. O processamento de dados ocorre via *streaming* (leitura e gravação linha a linha em arquivos `.jsonl`), e o pipeline de ingestão é executado em subprocessos isolados. Isso garante que a memória seja completamente liberada ao final de cada etapa do processamento documental.

## 2. Pipeline de Processamento (Módulos)

O sistema opera de forma linear, com scripts de responsabilidade única:

* **`drive_sync.py`**: Módulo de coleta. Realiza a sincronização autônoma e incremental com o Google Drive via Conta de Serviço.
* **`extractor.py` & `cleaner.py`**: Módulos de formatação. Extraem o texto bruto dos PDFs e utilizam heurísticas determinísticas para normalizar o conteúdo em Markdown semântico.
* **`tagger.py`**: Módulo de indexação. Utiliza LLM (temperatura 0.1) para extrair metadados precisos e gera um Hash MD5 único para o controle de integridade do documento.
* **`chunker.py`**: Realiza o fatiamento (chunking) semântico baseado na estrutura de seções do texto. Salva os blocos em formato de *streaming* (`.jsonl`) para baixo consumo de RAM.
* **`embedder.py`**: Módulo de vetorização. Implementa um **Cache Vetorial por Hash** local para evitar a re-vetorização de blocos já existentes no banco ChromaDB.
* **`search.py`**: Motor de busca. Utiliza *Decomposição Multi-Query Ancorada* para evitar desvios semânticos, realiza o re-ranqueamento com **FlashRank** e gera respostas com fundamentação teórica.
* **`watcher.py`**: O orquestrador. Executa o pipeline de ingestão sequencialmente em subprocessos isolados.

## 3. Rastreabilidade e Citações

Para mitigar o problema de alucinação em modelos generativos, o sistema adota engenharia de prompt restritiva. Toda afirmação ou conceito gerado na resposta final inclui obrigatoriamente a referência direta ao bloco de texto correspondente (exemplo: `[TRECHO 3]`). O modelo é instruído a admitir a ausência de informações caso a resposta não esteja nos documentos vetorizados.

## 4. Instalação e Configuração

*(Nota: O diretório `/data`, que armazena os PDFs e o banco vetorial, não é incluído no repositório; ele será criado automaticamente na primeira execução do sistema).*

### Passo 1: Clonar o Repositório e Preparar o Ambiente
No terminal, execute os comandos abaixo para clonar o projeto e criar o ambiente virtual:

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


* **Windows (Prompt de Comando - CMD ou PowerShell):**
```
python -m venv .venv
.\.venv\Scripts\activate

```

*(Nota: Se o PowerShell no Windows retornar um erro vermelho dizendo que a execução de scripts está desabilitada, rode o comando `Set-ExecutionPolicy Unrestricted -Scope CurrentUser`, confirme com 'S' ou 'Y', e tente ativar novamente).*

### Passo 2: Instalar Dependências

Com o ambiente virtual ativo (indicado por `(.venv)` no terminal), instale as bibliotecas necessárias:

```
pip install -r requirements.txt
```
*(As dependências incluem: `PyMuPDF`, `google-genai`, `chromadb`, `flashrank`, `google-api-python-client`)*.

### Passo 3: Configuração das APIs (Google Cloud e Gemini)

O sistema requer integração com o ecossistema Google. Siga estes passos rigorosamente:

1. **Google Cloud (Drive):** Acesse o [Google Cloud Console](https://console.cloud.google.com/), crie um projeto e gere uma **Conta de Serviço (Service Account)**.
2. **Chave JSON:** Dentro da Conta de Serviço, crie uma chave no formato JSON, faça o download e renomeie o arquivo para `credentials.json`, colocando-o na raiz do projeto.
3. **Google AI Studio (Gemini):** Gere uma chave de API no [Google AI Studio](https://aistudio.google.com/).
4. **Edição do arquivo de credenciais:** Abra o seu `credentials.json` e adicione manualmente os campos `api_key` e `folder_id` no início do arquivo:

```json
{
  "api_key": "SUA_CHAVE_GEMINI_AQUI",
  "folder_id": "ID_DA_SUA_PASTA_DO_DRIVE_AQUI",
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "seu-bot@seu-projeto.iam.gserviceaccount.com",
  ...
}

```

### Passo 4: Permissões no Google Drive

1. Vá até a pasta no Google Drive que contém os PDFs acadêmicos.
2. Compartilhe a pasta com o endereço de e-mail do seu bot (o `client_email` presente no seu `credentials.json`).
3. Atribua a permissão de **Leitor** (Viewer) ao bot para que ele possa baixar os arquivos.
4. O ID da pasta pode ser extraído da URL (exemplo: `drive.google.com/drive/folders/ID_DA_PASTA?hl=pt-br`). Certifique-se de que este ID está correto no seu `credentials.json`.

## 5. Utilização

Com o ambiente virtual **ativo** e credenciais configuradas, a utilização divide-se em dois processos:

**Para sincronizar documentos e atualizar a base de conhecimento:**
```
python src/watcher.py
```

**Para iniciar a interface de busca e consulta:**
```
python src/search.py
```

## 6. Código Aberto e Contribuições

Este é um projeto *open-source* com arquitetura documentada para facilitar modificações. O código pode ser clonado e adaptado livremente. Sinta-se à vontade para realizar *forks*, alterar a estrutura dos prompts ou customizar heurísticas de limpeza. Pull Requests com otimizações são bem-vindos.
