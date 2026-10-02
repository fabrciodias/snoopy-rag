-- ============================================================
-- 1. RETRIEVAL RESULTS
-- ============================================================
-- Materializa os resultados da recuperação como entidades
-- persistentes da investigação.
--
-- RetrievalResult != Evidence.
-- Um resultado pode posteriormente originar uma Evidence.

CREATE TABLE IF NOT EXISTS public.retrieval_results (
    id                  uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    investigation_id    uuid NOT NULL
        REFERENCES public.investigations(id)
        ON DELETE CASCADE,
    unit_id             bigint NOT NULL
        REFERENCES public.chunks(id)
        ON DELETE CASCADE,
    rank                integer NOT NULL,
    retrieval_score     double precision NOT NULL,
    metadata            jsonb DEFAULT '{}'::jsonb,
    created_at          timestamptz DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS retrieval_results_investigation_idx
    ON public.retrieval_results (investigation_id, rank);

CREATE INDEX IF NOT EXISTS retrieval_results_unit_idx
    ON public.retrieval_results (unit_id);


-- ============================================================
-- 2. INVESTIGATION STATUS
-- ============================================================
-- O Alpha precisa conseguir distinguir uma investigação em
-- processamento de uma investigação concluída.

ALTER TABLE public.investigations
    ADD CONSTRAINT investigations_status_check
    CHECK (
        status IN (
            'PROCESSING',
            'COMPLETED',
            'FAILED',
            'CANCELLED'
        )
    );


-- ============================================================
-- 3. EVIDENCE INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS evidences_investigation_idx
    ON public.evidences (investigation_id);

CREATE INDEX IF NOT EXISTS evidences_unit_idx
    ON public.evidences (unit_id);


-- ============================================================
-- 4. RLS
-- ============================================================

ALTER TABLE public.retrieval_results ENABLE ROW LEVEL SECURITY;

-- As policies de autorização serão refinadas com a camada
-- de autenticação/isolamento do Alpha.
-- Não criamos aqui uma política permissiva nova.