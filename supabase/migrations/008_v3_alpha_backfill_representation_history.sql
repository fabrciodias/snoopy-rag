-- ============================================================
-- V3 Alpha — Migração das representações legadas para histórico
-- ============================================================
--
-- A migration 005 criou o modelo histórico de representações,
-- mas documentos que já possuíam uma representação persistida
-- ainda a mantêm apenas em documents.representation.
--
-- Esta migration materializa essas representações no histórico
-- e associa cada documento à sua representação corrente.
--
-- A coluna documents.representation permanece temporariamente
-- para compatibilidade/transição, mas deixa de ser a fonte
-- principal de leitura.
-- ============================================================


INSERT INTO public.document_representations (
    id,
    document_id,
    representation
)
SELECT
    (d.representation ->> 'representation_id')::uuid,
    d.id,
    d.representation
FROM public.documents d
WHERE
    d.representation IS NOT NULL
    AND d.representation ? 'representation_id'
    AND (d.representation ->> 'representation_id')
        ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    AND NOT EXISTS (
        SELECT 1
        FROM public.document_representations dr
        WHERE dr.id =
            (d.representation ->> 'representation_id')::uuid
    );


UPDATE public.documents d
SET current_representation_id =
    (d.representation ->> 'representation_id')::uuid
WHERE
    d.current_representation_id IS NULL
    AND d.representation IS NOT NULL
    AND d.representation ? 'representation_id'
    AND (d.representation ->> 'representation_id')
        ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    AND EXISTS (
        SELECT 1
        FROM public.document_representations dr
        WHERE dr.id =
            (d.representation ->> 'representation_id')::uuid
        AND dr.document_id = d.id
    );