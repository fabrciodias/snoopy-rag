-- ============================================================
-- V3 Alpha — Alinhamento dos contratos de Operation e
-- Investigation
-- ============================================================
--
-- A migration 001 criou os modelos iniciais de operations e
-- investigations antes da consolidação dos contratos atuais
-- do domínio V3.
--
-- Esta migration alinha o schema persistente aos contratos
-- atualmente utilizados pela aplicação.
-- ============================================================


-- ============================================================
-- 1. OPERATIONS
-- ============================================================

ALTER TABLE public.operations
ADD COLUMN IF NOT EXISTS target_type text;


ALTER TABLE public.operations
DROP CONSTRAINT IF EXISTS operations_target_type_check;


ALTER TABLE public.operations
ADD CONSTRAINT operations_target_type_check
CHECK (
    target_type IS NULL
    OR target_type IN (
        'FOLDER',
        'DOCUMENT',
        'INVESTIGATION'
    )
);


CREATE INDEX IF NOT EXISTS operations_target_idx
ON public.operations (
    target_type,
    target_id
);


-- ============================================================
-- 2. INVESTIGATIONS
-- ============================================================

ALTER TABLE public.investigations
ADD COLUMN IF NOT EXISTS folder_id uuid;


ALTER TABLE public.investigations
DROP CONSTRAINT IF EXISTS investigations_folder_id_fkey;


ALTER TABLE public.investigations
ADD CONSTRAINT investigations_folder_id_fkey
FOREIGN KEY (folder_id)
REFERENCES public.folders(id)
ON DELETE CASCADE;


CREATE INDEX IF NOT EXISTS investigations_folder_id_idx
ON public.investigations (
    folder_id
);