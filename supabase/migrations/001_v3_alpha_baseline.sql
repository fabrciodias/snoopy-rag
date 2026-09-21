-- 1. ADAPTAÇÃO DA TABELA DE DOCUMENTOS (Document Processing)
-- Adiciona o controle de estados e a coluna para a DocumentRepresentation (JSONB)
ALTER TABLE "public"."documents"
  ADD COLUMN IF NOT EXISTS "status" text DEFAULT 'PENDING'::text,
  ADD COLUMN IF NOT EXISTS "representation" jsonb,
  ADD CONSTRAINT "documents_status_check" CHECK (status IN ('PENDING', 'PROCESSING', 'ACTIVE', 'FAILED', 'REJECTED', 'REMOVED'));

-- 2. ADAPTAÇÃO DA TABELA DE CHUNKS (Preparação para RetrievalUnit e Busca Híbrida)
-- Injeta localização espacial estruturada, ordenação e vetor de texto para o PostgreSQL FTS
ALTER TABLE "public"."chunks"
  ADD COLUMN IF NOT EXISTS "unit_index" integer,
  ADD COLUMN IF NOT EXISTS "location" jsonb,
  ADD COLUMN IF NOT EXISTS "fts" tsvector;

-- Cria índice GIN para acelerar a busca lexical nativa
CREATE INDEX IF NOT EXISTS chunks_fts_idx ON "public"."chunks" USING GIN (fts);

-- 3. CRIAÇÃO DA TABELA OPERATIONS (Execução Assíncrona Agnostica)
-- Substitui conceitualmente a tabela "jobs", servindo para qualquer processamento longo
CREATE TABLE IF NOT EXISTS "public"."operations" (
  "id"             uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
  "operation_type" text NOT NULL,
  "target_id"      text, 
  "status"         text DEFAULT 'PENDING'::text,
  "error_log"      text,
  "created_at"     timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  "started_at"     timestamp with time zone,
  "finished_at"    timestamp with time zone,
  CONSTRAINT "operations_status_check" CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'))
);

ALTER TABLE "public"."operations" ENABLE ROW LEVEL SECURITY;

-- 4. CRIAÇÃO DA TABELA INVESTIGATIONS (Contexto Investigativo)
-- Preserva o estado de uma pesquisa contínua e a StructuredResponse
CREATE TABLE IF NOT EXISTS "public"."investigations" (
  "id"                  uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
  "user_id"             uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  "original_query"      text NOT NULL,
  "filters"             jsonb DEFAULT '{}'::jsonb,
  "status"              text DEFAULT 'PROCESSING'::text,
  "structured_response" jsonb,
  "created_at"          timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE "public"."investigations" ENABLE ROW LEVEL SECURITY;

-- 5. CRIAÇÃO DA TABELA EVIDENCES (Proveniência Navegável)
-- Rastreia o salto semântico entre o resultado do Retrieval e a origem física
CREATE TABLE IF NOT EXISTS "public"."evidences" (
  "id"               uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
  "investigation_id" uuid REFERENCES public.investigations(id) ON DELETE CASCADE,
  "unit_id"          bigint REFERENCES public.chunks(id) ON DELETE CASCADE,
  "document_id"      uuid REFERENCES public.documents(id) ON DELETE CASCADE,
  "location"         jsonb,
  "content"          text NOT NULL,
  "context"          text,
  "provenance"       jsonb,
  "created_at"       timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE "public"."evidences" ENABLE ROW LEVEL SECURITY;