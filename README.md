# Snoopy-RAG V3 Alpha

O **Snoopy-RAG** é uma ferramenta de apoio à pesquisa acadêmica que permite explorar acervos de documentos PDF, recuperar trechos relevantes a partir de perguntas de pesquisa e examinar as evidências e suas fontes originais.

O projeto surgiu no contexto do GEPAFOR/UFMA, a partir da necessidade de pesquisar um acervo de trabalhos científicos armazenados no Google Drive. A proposta é facilitar a localização e a exploração do material documental, oferecendo ao pesquisador uma maneira de encontrar informações potencialmente relevantes sem perder a relação com os documentos de origem.

A **V3 Alpha** materializa uma nova arquitetura para o sistema, com maior separação entre documentos, representações documentais, unidades de recuperação, evidências e sínteses.

## Objetivo e funcionamento

O Snoopy-RAG busca reduzir o esforço necessário para localizar e examinar informações em um corpus documental. Em vez de apresentar somente uma resposta produzida por inteligência artificial, o sistema procura manter a relação entre a consulta, os trechos recuperados, seu contexto e a fonte documental.

Seu funcionamento pode ser compreendido em cinco etapas:

1. **Seleção do acervo:** o usuário autentica-se com sua conta Google e seleciona uma pasta do Google Drive que contenha documentos PDF.
2. **Processamento documental:** o sistema sincroniza os documentos e extrai seu conteúdo textual, preservando informações estruturais necessárias para localizar as passagens no documento de origem.
3. **Preparação para recuperação:** o conteúdo é organizado em unidades recuperáveis e associado a representações vetoriais, utilizadas na busca semântica.
4. **Investigação:** o usuário formula uma pergunta. O sistema combina busca textual e semântica para localizar trechos potencialmente relevantes no acervo.
5. **Exame das evidências:** os resultados podem ser explorados com seu contexto e sua origem documental. O sistema também utiliza um modelo de linguagem para produzir uma síntese baseada nas evidências recuperadas.

A recuperação de um trecho não significa, por si só, que ele seja metodologicamente relevante. Da mesma forma, uma síntese produzida por inteligência artificial não substitui a consulta à fonte nem a interpretação do pesquisador.

O Snoopy-RAG **não executa automaticamente um método de análise de conteúdo**, não determina definitivamente unidades de registro ou categorias analíticas e não substitui a responsabilidade do pesquisador pelas decisões metodológicas.

## Tecnologias utilizadas

A V3 Alpha utiliza as seguintes tecnologias e serviços:

* **Interface — Vue 3 e TypeScript:** apresentação e interação com o usuário.
* **Ferramentas do frontend — Vite:** desenvolvimento e compilação da interface.
* **Backend — Python, FastAPI e Uvicorn:** API e execução das operações da aplicação.
* **Processamento de PDFs — PyMuPDF:** extração de conteúdo textual e informações estruturais dos documentos.
* **Banco de dados — PostgreSQL, por meio do Supabase:** persistência dos documentos, representações, unidades recuperáveis, investigações e evidências.
* **Busca — PostgreSQL Full-Text Search e pgvector:** recuperação textual e semântica.
* **Inteligência artificial — Google Gemini API:** geração de embeddings e sínteses.
* **Acesso aos documentos — Google Drive API e Google Picker:** seleção de acervos e acesso aos documentos autorizados pelo usuário.
* **Autenticação — Supabase Auth com Google OAuth:** autenticação dos usuários.

O backend combina a recuperação textual e semântica para compor os resultados da pesquisa. O banco de dados mantém as informações necessárias para relacionar as unidades recuperadas aos documentos e às investigações correspondentes.

### Limites da V3 Alpha

A V3 Alpha materializa o núcleo funcional da nova arquitetura, mas não representa a implementação definitiva de todas as capacidades previstas para o Snoopy-RAG.

Entre seus limites atuais está a ausência de OCR. Portanto, documentos digitalizados que dependam de reconhecimento óptico de caracteres não são contemplados pelo processamento da Alpha. Outros recursos documentais avançados também permanecem fora do escopo desta versão.

## Requisitos

A execução do Snoopy-RAG V3 Alpha requer:

* **Git**, para obter o código-fonte.
* **Python 3.10 ou superior**, para executar o backend.
* **Node.js 20.19 ou superior, ou 22.12 ou superior**, e npm, para instalar as dependências, executar o frontend e compilar a versão de produção.
* **Projeto no Supabase**, com autenticação configurada e estrutura de banco compatível com a V3 Alpha.
* **Projeto no Google Cloud**, com as APIs e as credenciais necessárias à integração com o Google Drive e o Google Picker.
* **Chave de acesso à Google Gemini API**, para geração de embeddings e sínteses.

O PM2 é necessário para gerenciar a execução da aplicação em servidor Linux, mas não é necessário para o ambiente de desenvolvimento.

## Serviços externos e credenciais

### Google Cloud e Google Drive

A integração com o Google requer:

* **Google Drive API**, para acessar os documentos autorizados pelo usuário.
* **Google Picker API**, para selecionar pastas do Google Drive na interface.
* **Chave de API**, configurada para utilização pelo Google Picker.
* **Número do projeto Google Cloud**, utilizado como identificador da aplicação no Picker.
* **Credenciais OAuth 2.0**, integradas ao provedor Google do Supabase Auth, para autenticação e autorização de acesso ao Drive.

O fluxo de autenticação solicita a permissão de leitura do Google Drive (`drive.readonly`). O acesso aos documentos depende da autorização concedida pelo usuário autenticado.

### Google Gemini

É necessária uma chave de API válida para os modelos utilizados na aplicação.

As variáveis `GEMINI_LLM_MODEL` e `GEMINI_EMBEDDING_MODEL` definem, respectivamente, os modelos utilizados para a geração de sínteses e de embeddings. Os identificadores padrão estão definidos no arquivo `.env.example`.

### Supabase

A configuração do Supabase requer:

* **URL do projeto**, utilizada para estabelecer a conexão com o serviço.
* **Chave pública do projeto**, utilizada pelo frontend.
* **Chave `service_role`**, utilizada pelo backend.
* **Banco PostgreSQL com pgvector** e a estrutura necessária à persistência documental e à recuperação híbrida.

A estrutura deve incluir as tabelas, os índices e as funções SQL exigidos pela V3 Alpha, incluindo os recursos utilizados na busca textual e vetorial. O arquivo [`supabase/schema_supabase.sql`](./supabase/schema_supabase.sql) contém o esquema de referência presente no repositório.

## Instalação

### 1. Obtenção do código-fonte

O repositório pode ser clonado com os seguintes comandos:

```bash
git clone https://github.com/fabrciodias/snoopy-rag.git
cd snoopy-rag
```

### 2. Criação do ambiente virtual Python

A criação de um ambiente virtual permite isolar as dependências Python do projeto.

**Windows — PowerShell**

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

É necessário manter o ambiente virtual ativo para executar o backend.

Em distribuições Debian e Ubuntu, caso o módulo `venv` não esteja disponível, pode ser necessário instalar o pacote `python3-venv` correspondente à versão do Python do sistema.

### 3. Instalação das dependências do frontend

As dependências JavaScript são instaladas a partir do arquivo `frontend/package-lock.json`.

```bash
cd frontend
npm ci
cd ..
```

O comando `npm ci` instala as dependências registradas no arquivo de bloqueio, respeitando as versões definidas pelo projeto.

### 4. Configuração das variáveis de ambiente

O arquivo `.env` deve ser criado na raiz do repositório a partir do modelo `.env.example`.

**Windows — PowerShell**

```powershell
Copy-Item .env.example .env
```

**Linux**

```bash
cp .env.example .env
```

O arquivo `.env` contém as credenciais e os parâmetros utilizados pelo backend. As variáveis de configuração são:

* `GOOGLE_API_KEY`: chave de API do Google Picker.
* `GOOGLE_APP_ID`: número do projeto Google Cloud utilizado pelo Picker.
* `SUPABASE_URL`: endereço do projeto Supabase.
* `SUPABASE_KEY`: chave pública do Supabase.
* `SUPABASE_SERVICE_KEY`: chave privada de serviço do Supabase.
* `GEMINI_API_KEY`: chave de acesso à Google Gemini API.
* `GEMINI_LLM_MODEL`: identificador do modelo de linguagem utilizado para gerar sínteses.
* `GEMINI_EMBEDDING_MODEL`: identificador do modelo utilizado para gerar embeddings.
* `RETRIEVAL_DEFAULT_LIMIT`: quantidade padrão de resultados considerados na recuperação.
* `RETRIEVAL_MAX_LIMIT`: limite máximo de resultados da recuperação.
* `GEMINI_EMBEDDING_BATCH_SIZE`: quantidade de textos processados por lote na geração de embeddings.
* `ENVIRONMENT`: identificação do ambiente de execução.
* `API_PORT`: porta de execução da API, com valor padrão `3000`.

As credenciais e os identificadores específicos devem corresponder aos serviços externos configurados para o ambiente de execução.

O arquivo `.env` contém informações sensíveis e não deve ser incluído no controle de versão.

## Execução em ambiente de desenvolvimento

Durante o desenvolvimento, o backend e o frontend são executados em processos separados.

### Backend

Com o ambiente virtual Python ativo, o backend pode ser iniciado na raiz do projeto:

```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 3000 --reload
```

A API ficará disponível em `http://127.0.0.1:3000`.

A opção `--reload` reinicia o backend quando alterações nos arquivos Python são detectadas, sendo destinada ao ambiente de desenvolvimento.

### Frontend

Em outro terminal, na raiz do repositório:

```bash
cd frontend
npm run dev
```

O frontend ficará disponível, por padrão, em `http://localhost:5173`.

O servidor Vite encaminha as requisições da aplicação ao backend na porta `3000`. Ambos os processos precisam estar em execução para o funcionamento do ambiente de desenvolvimento.

## Execução em servidor Linux

Em servidor Linux, o PM2 gerencia o processo do backend, enquanto o FastAPI disponibiliza a interface compilada e a API pela porta `3000`.

Após a configuração do ambiente virtual Python, das dependências e das variáveis de ambiente, a instalação do PM2 pode ser realizada globalmente:

```bash
npm install --global pm2
```

Na pasta do frontend, a instalação das dependências e a inicialização da aplicação são realizadas com:

```bash
cd frontend
npm ci
npm start
```

O comando `npm start` compila o frontend para produção, inicia ou reinicia o processo `snoopy-rag-v3` no PM2 e salva a lista de processos gerenciados.

Os comandos adicionais disponíveis nessa pasta são:

* `npm run status`: exibe o estado dos processos gerenciados pelo PM2.
* `npm run logs`: acompanha os logs do processo `snoopy-rag-v3`.
* `npm run stop`: remove o processo `snoopy-rag-v3` da lista de processos do PM2.

Para restaurar a aplicação automaticamente após a reinicialização do sistema, é necessário configurar o mecanismo de inicialização do PM2. O procedimento consiste em executar `pm2 startup`, aplicar o comando de configuração apresentado pelo próprio PM2 e executar `pm2 save` para registrar a lista de processos que deverá ser restaurada.

## Considerações finais

O Snoopy-RAG V3 Alpha estabelece uma infraestrutura de apoio à exploração documental na qual a pergunta de pesquisa, os trechos recuperados e os documentos de origem permanecem relacionados. A geração de sínteses auxilia a compreensão inicial dos resultados, enquanto o acesso às evidências e às fontes permite examinar o material que fundamenta essas respostas.

Essa continuidade entre recuperação, evidência e fonte constitui um dos princípios centrais do projeto. A ferramenta apoia o trabalho investigativo sem substituir a análise e a interpretação realizadas pelo pesquisador.

## Licença

O Snoopy-RAG é distribuído sob a licença [MIT](./LICENSE).
