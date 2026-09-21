CREATE OR REPLACE FUNCTION v3_hybrid_search (
  p_query_text text,
  p_query_embedding vector(768),
  p_match_count int,
  p_user_id uuid,
  p_folder_id uuid
) RETURNS TABLE (
  unit_id bigint,
  document_id uuid,
  content text,
  location jsonb,
  semantic_score double precision,
  lexical_score double precision
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  WITH semantic_search AS (
    SELECT c.id, (1 - (c.embedding <=> p_query_embedding)) AS score
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE d.status = 'ACTIVE' 
      AND c.folder_id = p_folder_id 
      AND (c.user_id = p_user_id OR p_folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62')
    ORDER BY c.embedding <=> p_query_embedding
    LIMIT p_match_count * 2
  ),
  lexical_search AS (
    SELECT c.id, ts_rank(c.fts, websearch_to_tsquery('portuguese', p_query_text)) AS score
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE d.status = 'ACTIVE' 
      AND c.folder_id = p_folder_id 
      AND (c.user_id = p_user_id OR p_folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62')
      AND c.fts @@ websearch_to_tsquery('portuguese', p_query_text)
    ORDER BY score DESC
    LIMIT p_match_count * 2
  )
  SELECT
    c.id AS unit_id, 
    c.document_id, 
    c.content, 
    c.location,
    COALESCE(s.score, 0.0)::double precision AS semantic_score,
    COALESCE(l.score, 0.0)::double precision AS lexical_score
  FROM chunks c
  LEFT JOIN semantic_search s ON c.id = s.id
  LEFT JOIN lexical_search l ON c.id = l.id
  WHERE s.id IS NOT NULL OR l.id IS NOT NULL;
END;
$$;