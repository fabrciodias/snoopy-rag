CREATE OR REPLACE FUNCTION public.v3_hybrid_search (
    p_query_text text,
    p_query_embedding vector(768),
    p_match_count integer,
    p_user_id uuid,
    p_folder_id uuid
)
RETURNS TABLE (
    unit_id bigint,
    document_id uuid,
    content text,
    location jsonb,
    semantic_score double precision,
    lexical_score double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY

    WITH semantic_search AS (
        SELECT
            c.id,
            1 - (c.embedding <=> p_query_embedding)
                AS score
        FROM public.chunks c
        JOIN public.documents d
            ON c.document_id = d.id
        WHERE
            d.status = 'ACTIVE'
            AND c.folder_id = p_folder_id
            AND (
                c.user_id = p_user_id
                OR EXISTS (
                    SELECT 1
                    FROM public.folders f
                    WHERE
                        f.id = p_folder_id
                        AND f.user_id IS NULL
                )
            )
        ORDER BY c.embedding <=> p_query_embedding
        LIMIT p_match_count * 2
    ),

    lexical_search AS (
        SELECT
            c.id,
            ts_rank(
                c.fts,
                websearch_to_tsquery(
                    'portuguese',
                    p_query_text
                )
            ) AS score
        FROM public.chunks c
        JOIN public.documents d
            ON c.document_id = d.id
        WHERE
            d.status = 'ACTIVE'
            AND c.folder_id = p_folder_id
            AND (
                c.user_id = p_user_id
                OR EXISTS (
                    SELECT 1
                    FROM public.folders f
                    WHERE
                        f.id = p_folder_id
                        AND f.user_id IS NULL
                )
            )
            AND c.fts @@ websearch_to_tsquery(
                'portuguese',
                p_query_text
            )
        ORDER BY score DESC
        LIMIT p_match_count * 2
    )

    SELECT
        c.id AS unit_id,
        c.document_id,
        c.content,
        c.location,
        COALESCE(
            semantic_search.score,
            0.0
        )::double precision AS semantic_score,
        COALESCE(
            lexical_search.score,
            0.0
        )::double precision AS lexical_score

    FROM public.chunks c

    LEFT JOIN semantic_search
        ON c.id = semantic_search.id

    LEFT JOIN lexical_search
        ON c.id = lexical_search.id

    WHERE
        semantic_search.id IS NOT NULL
        OR lexical_search.id IS NOT NULL;
END;
$$;