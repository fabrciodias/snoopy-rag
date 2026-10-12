--
-- PostgreSQL database dump
--

\restrict 5bvYOkQJaX1c1nJotRBl3fLr7ufEC6WvEQxa3ww97qQ3LaDm2lqt9zf2HAUEzfQ

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: chunks_update_fts(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.chunks_update_fts() RETURNS trigger
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


--
-- Name: match_chunks(public.vector, double precision, integer, uuid, uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.match_chunks(query_embedding public.vector, match_threshold double precision, match_count integer, p_user_id uuid, p_folder_id uuid) RETURNS TABLE(id bigint, document_id uuid, content text, section text, similarity double precision, title text, authors text[], publication_year text, drive_link text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.content,
        c.section,
        1 - (c.embedding <=> query_embedding) AS similarity,
        d.title,
        d.authors,           
        d.publication_year,  
        d.drive_link
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.folder_id = p_folder_id 
      AND (c.user_id = p_user_id OR p_folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62')
      AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


--
-- Name: v3_hybrid_search(text, public.vector, integer, uuid, uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.v3_hybrid_search(p_query_text text, p_query_embedding public.vector, p_match_count integer, p_user_id uuid, p_folder_id uuid) RETURNS TABLE(unit_id bigint, document_id uuid, representation_id uuid, content text, location jsonb, semantic_score double precision, lexical_score double precision)
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
            AND c.representation_id =
                d.current_representation_id
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
            AND c.representation_id =
                d.current_representation_id
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
        c.representation_id,
        c.content,
        c.location,

        semantic_search.score::double precision
            AS semantic_score,

        lexical_search.score::double precision
            AS lexical_score

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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chunks (
    id bigint NOT NULL,
    user_id uuid,
    folder_id uuid,
    document_id uuid,
    content text NOT NULL,
    section text,
    embedding public.vector(768),
    unit_index integer,
    location jsonb,
    fts tsvector,
    representation_id uuid
);


--
-- Name: chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chunks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chunks_id_seq OWNED BY public.chunks.id;


--
-- Name: document_representations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_representations (
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    representation jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    folder_id uuid,
    title text NOT NULL,
    authors text[],
    publication_year text,
    document_hash text NOT NULL,
    drive_link text,
    drive_file_id text,
    content text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    status text DEFAULT 'PENDING'::text,
    representation jsonb,
    current_representation_id uuid,
    document_type text,
    language text,
    keywords text[] DEFAULT '{}'::text[] NOT NULL,
    drive_file_name text,
    mime_type text,
    CONSTRAINT documents_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'PROCESSING'::text, 'ACTIVE'::text, 'FAILED'::text, 'REJECTED'::text, 'REMOVED'::text])))
);


--
-- Name: evidences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evidences (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    investigation_id uuid,
    unit_id bigint,
    document_id uuid,
    location jsonb,
    content text NOT NULL,
    context text,
    provenance jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


--
-- Name: folders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folders (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    name text NOT NULL,
    drive_id text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


--
-- Name: investigations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.investigations (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    original_query text NOT NULL,
    filters jsonb DEFAULT '{}'::jsonb,
    status text DEFAULT 'PROCESSING'::text,
    structured_response jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    folder_id uuid,
    CONSTRAINT investigations_status_check CHECK ((status = ANY (ARRAY['PROCESSING'::text, 'COMPLETED'::text, 'FAILED'::text, 'CANCELLED'::text])))
);


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    folder_id uuid,
    file_name text NOT NULL,
    drive_file_id text,
    status text DEFAULT 'pending'::text,
    error_log text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    progress integer DEFAULT 0,
    CONSTRAINT jobs_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text])))
);


--
-- Name: operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operations (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    operation_type text NOT NULL,
    target_id text,
    status text DEFAULT 'PENDING'::text,
    error_log text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    target_type text,
    progress jsonb,
    CONSTRAINT operations_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'PROCESSING'::text, 'COMPLETED'::text, 'FAILED'::text, 'CANCELLED'::text]))),
    CONSTRAINT operations_target_type_check CHECK (((target_type IS NULL) OR (target_type = ANY (ARRAY['FOLDER'::text, 'DOCUMENT'::text, 'INVESTIGATION'::text]))))
);


--
-- Name: COLUMN operations.progress; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.operations.progress IS 'Progresso estruturado da operação, persistido para recuperação e acompanhamento pelo frontend.';


--
-- Name: retrieval_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.retrieval_results (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    investigation_id uuid NOT NULL,
    unit_id bigint NOT NULL,
    rank integer NOT NULL,
    retrieval_score double precision NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    representation_id uuid,
    content text,
    document_id uuid NOT NULL,
    semantic_score double precision,
    lexical_score double precision,
    location jsonb
);


--
-- Name: search_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.search_history (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    folder_id uuid,
    query text NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    investigation_id uuid
);


--
-- Name: chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks ALTER COLUMN id SET DEFAULT nextval('public.chunks_id_seq'::regclass);


--
-- Name: chunks chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks
    ADD CONSTRAINT chunks_pkey PRIMARY KEY (id);


--
-- Name: document_representations document_representations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_representations
    ADD CONSTRAINT document_representations_pkey PRIMARY KEY (id);


--
-- Name: documents documents_folder_id_document_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_folder_id_document_hash_key UNIQUE (folder_id, document_hash);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: evidences evidences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidences
    ADD CONSTRAINT evidences_pkey PRIMARY KEY (id);


--
-- Name: folders folders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folders
    ADD CONSTRAINT folders_pkey PRIMARY KEY (id);


--
-- Name: folders folders_user_id_drive_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folders
    ADD CONSTRAINT folders_user_id_drive_id_key UNIQUE (user_id, drive_id);


--
-- Name: investigations investigations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigations
    ADD CONSTRAINT investigations_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: operations operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operations
    ADD CONSTRAINT operations_pkey PRIMARY KEY (id);


--
-- Name: retrieval_results retrieval_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retrieval_results
    ADD CONSTRAINT retrieval_results_pkey PRIMARY KEY (id);


--
-- Name: search_history search_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_history
    ADD CONSTRAINT search_history_pkey PRIMARY KEY (id);


--
-- Name: chunks_document_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chunks_document_id_idx ON public.chunks USING btree (document_id);


--
-- Name: chunks_fts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chunks_fts_idx ON public.chunks USING gin (fts);


--
-- Name: chunks_representation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chunks_representation_id_idx ON public.chunks USING btree (representation_id);


--
-- Name: document_representations_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX document_representations_created_at_idx ON public.document_representations USING btree (created_at);


--
-- Name: document_representations_document_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX document_representations_document_id_idx ON public.document_representations USING btree (document_id);


--
-- Name: document_representations_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX document_representations_id_idx ON public.document_representations USING btree (id);


--
-- Name: evidences_investigation_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evidences_investigation_idx ON public.evidences USING btree (investigation_id);


--
-- Name: evidences_unit_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evidences_unit_idx ON public.evidences USING btree (unit_id);


--
-- Name: investigations_folder_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX investigations_folder_id_idx ON public.investigations USING btree (folder_id);


--
-- Name: operations_one_active_drive_sync_per_folder_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX operations_one_active_drive_sync_per_folder_idx ON public.operations USING btree (target_id) WHERE ((operation_type = 'DRIVE_SYNC'::text) AND (target_type = 'FOLDER'::text) AND (status = ANY (ARRAY['PENDING'::text, 'PROCESSING'::text])));


--
-- Name: operations_target_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX operations_target_idx ON public.operations USING btree (target_type, target_id);


--
-- Name: retrieval_results_investigation_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX retrieval_results_investigation_idx ON public.retrieval_results USING btree (investigation_id, rank);


--
-- Name: retrieval_results_representation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX retrieval_results_representation_id_idx ON public.retrieval_results USING btree (representation_id);


--
-- Name: retrieval_results_unit_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX retrieval_results_unit_idx ON public.retrieval_results USING btree (unit_id);


--
-- Name: search_history_investigation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX search_history_investigation_id_idx ON public.search_history USING btree (investigation_id);


--
-- Name: chunks chunks_fts_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chunks_fts_trigger BEFORE INSERT OR UPDATE OF content ON public.chunks FOR EACH ROW EXECUTE FUNCTION public.chunks_update_fts();


--
-- Name: chunks chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks
    ADD CONSTRAINT chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: chunks chunks_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks
    ADD CONSTRAINT chunks_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;


--
-- Name: chunks chunks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks
    ADD CONSTRAINT chunks_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: document_representations document_representations_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_representations
    ADD CONSTRAINT document_representations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: documents documents_current_representation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_current_representation_id_fkey FOREIGN KEY (current_representation_id) REFERENCES public.document_representations(id) ON DELETE SET NULL;


--
-- Name: documents documents_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;


--
-- Name: documents documents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: evidences evidences_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidences
    ADD CONSTRAINT evidences_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: evidences evidences_investigation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidences
    ADD CONSTRAINT evidences_investigation_id_fkey FOREIGN KEY (investigation_id) REFERENCES public.investigations(id) ON DELETE CASCADE;


--
-- Name: evidences evidences_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidences
    ADD CONSTRAINT evidences_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.chunks(id) ON DELETE CASCADE;


--
-- Name: folders folders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folders
    ADD CONSTRAINT folders_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: investigations investigations_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigations
    ADD CONSTRAINT investigations_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;


--
-- Name: investigations investigations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigations
    ADD CONSTRAINT investigations_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: retrieval_results retrieval_results_investigation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retrieval_results
    ADD CONSTRAINT retrieval_results_investigation_id_fkey FOREIGN KEY (investigation_id) REFERENCES public.investigations(id) ON DELETE CASCADE;


--
-- Name: retrieval_results retrieval_results_representation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retrieval_results
    ADD CONSTRAINT retrieval_results_representation_id_fkey FOREIGN KEY (representation_id) REFERENCES public.document_representations(id) ON DELETE SET NULL;


--
-- Name: retrieval_results retrieval_results_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retrieval_results
    ADD CONSTRAINT retrieval_results_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.chunks(id) ON DELETE CASCADE;


--
-- Name: search_history search_history_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_history
    ADD CONSTRAINT search_history_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;


--
-- Name: search_history search_history_investigation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_history
    ADD CONSTRAINT search_history_investigation_id_fkey FOREIGN KEY (investigation_id) REFERENCES public.investigations(id) ON DELETE CASCADE;


--
-- Name: search_history search_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_history
    ADD CONSTRAINT search_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: search_history Acesso ao próprio histórico; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Acesso ao próprio histórico" ON public.search_history USING ((auth.uid() = user_id));


--
-- Name: folders Acesso aos próprios acervos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Acesso aos próprios acervos" ON public.folders USING ((auth.uid() = user_id));


--
-- Name: chunks Acesso aos próprios chunks; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Acesso aos próprios chunks" ON public.chunks USING ((auth.uid() = user_id));


--
-- Name: documents Acesso aos próprios documentos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Acesso aos próprios documentos" ON public.documents USING ((auth.uid() = user_id));


--
-- Name: jobs Acesso aos próprios jobs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Acesso aos próprios jobs" ON public.jobs USING ((auth.uid() = user_id));


--
-- Name: folders Leitura pública do acervo GEPAFOR; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Leitura pública do acervo GEPAFOR" ON public.folders FOR SELECT USING ((id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::uuid));


--
-- Name: chunks Leitura pública dos chunks GEPAFOR; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Leitura pública dos chunks GEPAFOR" ON public.chunks FOR SELECT USING ((folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::uuid));


--
-- Name: documents Leitura pública dos documentos GEPAFOR; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Leitura pública dos documentos GEPAFOR" ON public.documents FOR SELECT USING ((folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::uuid));


--
-- Name: chunks; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.chunks ENABLE ROW LEVEL SECURITY;

--
-- Name: document_representations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.document_representations ENABLE ROW LEVEL SECURITY;

--
-- Name: documents; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

--
-- Name: evidences; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.evidences ENABLE ROW LEVEL SECURITY;

--
-- Name: folders; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.folders ENABLE ROW LEVEL SECURITY;

--
-- Name: investigations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.investigations ENABLE ROW LEVEL SECURITY;

--
-- Name: jobs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

--
-- Name: operations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.operations ENABLE ROW LEVEL SECURITY;

--
-- Name: retrieval_results; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.retrieval_results ENABLE ROW LEVEL SECURITY;

--
-- Name: search_history; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.search_history ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--

\unrestrict 5bvYOkQJaX1c1nJotRBl3fLr7ufEC6WvEQxa3ww97qQ3LaDm2lqt9zf2HAUEzfQ

