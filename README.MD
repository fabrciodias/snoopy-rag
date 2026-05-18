# Snoopy-RAG V2: Motor Semântico Documental

Sistema RAG (Retrieval-Augmented Generation) focado em pesquisa acadêmica. Indexa e consulta PDFs (artigos, teses, livros) garantindo rastreabilidade exata (1:1) das fontes e mitigação de alucinações.

> **Nota de Evolução:** Para contornar gargalos de um hardware físico restrito (servidor de produção rodando em um Megaware 2011, i3 2ª Gen, 4GB RAM DDR3, Ubuntu 22.04), a V2 substituiu o processamento local pesado (I/O de disco) por uma arquitetura de microsserviços em memória e nuvem. A documentação da infraestrutura legada (ingestão local + ChromaDB) foi preservada no [README_V1.md](./README_V1.md).

---

## 1. Arquitetura do Sistema (V2 Core)

* **Frontend (ES6):** Vanilla JS modularizado. Consome streams de resposta e logs do servidor via Server-Sent Events (SSE).
* **Middleware (Node.js/Express):** Roteador assíncrono. Implementa **Cache Semântico via Hash MD5**, interceptando queries repetidas para anular latência e custos redundantes de API.
* **Motor Efêmero (Python):** O ETL (`pipeline.py`) opera estritamente em RAM. As etapas de extração, limpeza (Markdown), chunking e vetorização ocorrem sem persistência local. O arquivo original é descartado imediatamente após o processamento.
* **Banco Vetorial (Supabase / pgvector):** Arquitetura multi-tenant. O isolamento de acervos é garantido no banco relacional, restringindo a busca semântica ao `folder_id` autorizado do usuário.

## 2. Rastreabilidade Acadêmica

A engenharia de prompt impõe ancoragem estrita. Toda afirmação gerada pelo LLM inclui a citação do bloco de texto original (ex: `[TRECHO X]`). A interface isola a resposta (esquerda) das evidências originais (direita), garantindo verificação auditável.

## 3. Infraestrutura e Deploy

Projetado para rodar em servidores locais resilientes sem exposição de portas (NAT/CGNAT):
* **Rede (Cloudflare Tunnels):** Comunicação *outbound* via `http2` fornecendo Proxy Reverso e SSL na borda (Zero Trust).
* **Processos (PM2):** Node.js configurado como *daemon* (background) para reinicialização automática e recuperação de falhas (reboots/quedas de energia).

---

## 4. Setup e Execução

### Pré-requisitos
* Node.js v20+ / Python 3.10+
* Supabase (Projeto com pgvector)
* Google Cloud Console (Drive API e Google Picker habilitados)

### Instalação

1. Clone e instale as dependências:
```bash
git clone https://github.com/fabrciodias/snoopy-rag.git
cd snoopy-rag
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

2. Configure as variáveis de ambiente (`.env` na raiz):

```env
SUPABASE_URL=[https://sua-url.supabase.co](https://sua-url.supabase.co)
SUPABASE_KEY=sua-anon-key
SUPABASE_SERVICE_KEY=sua-service-role-key
GEMINI_API_KEY=sua-chave-gemini
GOOGLE_API_KEY=sua-chave-api-google
GOOGLE_APP_ID=seu-app-id

```

3. Inicie o servidor em background:

```bash
pm2 start server.js --name "snoopy-rag"
pm2 save
pm2 startup

```

## 5. Licença

Este projeto é distribuído sob a licença **MIT**. A arquitetura, o código e a infraestrutura são livres para uso, modificação e distribuição, seja para fins acadêmicos ou comerciais. Veja o arquivo `LICENSE` para os termos completos.