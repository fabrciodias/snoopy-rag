ALTER TABLE public.chunks
ADD COLUMN IF NOT EXISTS representation_id uuid;

CREATE INDEX IF NOT EXISTS chunks_document_id_idx
ON public.chunks(document_id);

CREATE INDEX IF NOT EXISTS chunks_representation_id_idx
ON public.chunks(representation_id);


-- Garante que o índice lexical seja realmente alimentado
CREATE OR REPLACE FUNCTION public.chunks_update_fts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.fts :=
        to_tsvector(
            'portuguese',
            COALESCE(NEW.content, '')
        );

    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS chunks_fts_trigger
ON public.chunks;

CREATE TRIGGER chunks_fts_trigger
BEFORE INSERT OR UPDATE OF content
ON public.chunks
FOR EACH ROW
EXECUTE FUNCTION public.chunks_update_fts();


-- Dados antigos também precisam ter FTS válido.
UPDATE public.chunks
SET fts = to_tsvector(
    'portuguese',
    COALESCE(content, '')
)
WHERE fts IS NULL;