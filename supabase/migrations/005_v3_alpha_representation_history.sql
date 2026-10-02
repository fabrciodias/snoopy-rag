-- ============================================================
-- V3 Alpha — Histórico de representações documentais
-- ============================================================


-- ============================================================
-- Documentos
-- ============================================================

ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS current_representation_id uuid;


-- ============================================================
-- Histórico de representações
-- ============================================================

CREATE TABLE IF NOT EXISTS public.document_representations (
    id uuid PRIMARY KEY,

    document_id uuid NOT NULL
        REFERENCES public.documents(id)
        ON DELETE CASCADE,

    representation jsonb NOT NULL,

    created_at timestamptz NOT NULL
        DEFAULT now()
);


CREATE INDEX IF NOT EXISTS
document_representations_document_id_idx
ON public.document_representations(document_id);


CREATE INDEX IF NOT EXISTS
document_representations_created_at_idx
ON public.document_representations(created_at);


-- ============================================================
-- Representação corrente do documento
-- ============================================================

ALTER TABLE public.documents
DROP CONSTRAINT IF EXISTS
documents_current_representation_id_fkey;


ALTER TABLE public.documents
ADD CONSTRAINT
documents_current_representation_id_fkey
FOREIGN KEY (current_representation_id)
REFERENCES public.document_representations(id)
ON DELETE SET NULL;


-- ============================================================
-- Resultados de recuperação
-- ============================================================

ALTER TABLE public.retrieval_results
ADD COLUMN IF NOT EXISTS representation_id uuid;


ALTER TABLE public.retrieval_results
DROP CONSTRAINT IF EXISTS
retrieval_results_representation_id_fkey;


ALTER TABLE public.retrieval_results
ADD CONSTRAINT
retrieval_results_representation_id_fkey
FOREIGN KEY (representation_id)
REFERENCES public.document_representations(id)
ON DELETE SET NULL;


CREATE INDEX IF NOT EXISTS
retrieval_results_representation_id_idx
ON public.retrieval_results(representation_id);
