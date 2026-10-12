-- ============================================================
-- V3 Alpha — Progresso persistido das operações
-- ============================================================
--
-- O progresso é uma representação do estado operacional
-- de uma execução identificada por operation_id.
--
-- A estrutura específica é validada pelo contrato Operation
-- no backend. A API continua sendo a fonte autoritativa.
-- ============================================================

ALTER TABLE public.operations
ADD COLUMN IF NOT EXISTS progress jsonb;

COMMENT ON COLUMN public.operations.progress IS
'Progresso estruturado da operação, persistido para recuperação e acompanhamento pelo frontend.';