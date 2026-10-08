ALTER TABLE public.search_history
ADD COLUMN IF NOT EXISTS investigation_id uuid;

ALTER TABLE public.search_history
DROP CONSTRAINT IF EXISTS search_history_investigation_id_fkey;

ALTER TABLE public.search_history
ADD CONSTRAINT search_history_investigation_id_fkey
FOREIGN KEY (investigation_id)
REFERENCES public.investigations(id)
ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS
search_history_investigation_id_idx
ON public.search_history(investigation_id);