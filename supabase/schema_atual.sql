


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE OR REPLACE FUNCTION "public"."chunks_update_fts"() RETURNS "trigger"
    LANGUAGE "plpgsql"
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


ALTER FUNCTION "public"."chunks_update_fts"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") RETURNS TABLE("id" bigint, "document_id" "uuid", "content" "text", "section" "text", "similarity" double precision, "title" "text", "authors" "text"[], "publication_year" "text", "drive_link" "text")
    LANGUAGE "plpgsql"
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


ALTER FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."v3_hybrid_search"("p_query_text" "text", "p_query_embedding" "public"."vector", "p_match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") RETURNS TABLE("unit_id" bigint, "document_id" "uuid", "representation_id" "uuid", "content" "text", "location" "jsonb", "semantic_score" double precision, "lexical_score" double precision)
    LANGUAGE "plpgsql"
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


ALTER FUNCTION "public"."v3_hybrid_search"("p_query_text" "text", "p_query_embedding" "public"."vector", "p_match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."chunks" (
    "id" bigint NOT NULL,
    "user_id" "uuid",
    "folder_id" "uuid",
    "document_id" "uuid",
    "content" "text" NOT NULL,
    "section" "text",
    "embedding" "public"."vector"(768),
    "unit_index" integer,
    "location" "jsonb",
    "fts" "tsvector",
    "representation_id" "uuid"
);


ALTER TABLE "public"."chunks" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."chunks_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."chunks_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."chunks_id_seq" OWNED BY "public"."chunks"."id";



CREATE TABLE IF NOT EXISTS "public"."document_representations" (
    "id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "representation" "jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."document_representations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."documents" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "folder_id" "uuid",
    "title" "text" NOT NULL,
    "authors" "text"[],
    "publication_year" "text",
    "document_hash" "text" NOT NULL,
    "drive_link" "text",
    "drive_file_id" "text",
    "content" "text",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "status" "text" DEFAULT 'PENDING'::"text",
    "representation" "jsonb",
    "current_representation_id" "uuid",
    CONSTRAINT "documents_status_check" CHECK (("status" = ANY (ARRAY['PENDING'::"text", 'PROCESSING'::"text", 'ACTIVE'::"text", 'FAILED'::"text", 'REJECTED'::"text", 'REMOVED'::"text"])))
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."evidences" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "investigation_id" "uuid",
    "unit_id" bigint,
    "document_id" "uuid",
    "location" "jsonb",
    "content" "text" NOT NULL,
    "context" "text",
    "provenance" "jsonb",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


ALTER TABLE "public"."evidences" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."folders" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "name" "text" NOT NULL,
    "drive_id" "text",
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


ALTER TABLE "public"."folders" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."investigations" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "original_query" "text" NOT NULL,
    "filters" "jsonb" DEFAULT '{}'::"jsonb",
    "status" "text" DEFAULT 'PROCESSING'::"text",
    "structured_response" "jsonb",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "folder_id" "uuid",
    CONSTRAINT "investigations_status_check" CHECK (("status" = ANY (ARRAY['PROCESSING'::"text", 'COMPLETED'::"text", 'FAILED'::"text", 'CANCELLED'::"text"])))
);


ALTER TABLE "public"."investigations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."jobs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "folder_id" "uuid",
    "file_name" "text" NOT NULL,
    "drive_file_id" "text",
    "status" "text" DEFAULT 'pending'::"text",
    "error_log" "text",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "progress" integer DEFAULT 0,
    CONSTRAINT "jobs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."jobs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."operations" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "operation_type" "text" NOT NULL,
    "target_id" "text",
    "status" "text" DEFAULT 'PENDING'::"text",
    "error_log" "text",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "started_at" timestamp with time zone,
    "finished_at" timestamp with time zone,
    "target_type" "text",
    CONSTRAINT "operations_status_check" CHECK (("status" = ANY (ARRAY['PENDING'::"text", 'PROCESSING'::"text", 'COMPLETED'::"text", 'FAILED'::"text", 'CANCELLED'::"text"]))),
    CONSTRAINT "operations_target_type_check" CHECK ((("target_type" IS NULL) OR ("target_type" = ANY (ARRAY['FOLDER'::"text", 'DOCUMENT'::"text", 'INVESTIGATION'::"text"]))))
);


ALTER TABLE "public"."operations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."retrieval_results" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "investigation_id" "uuid" NOT NULL,
    "unit_id" bigint NOT NULL,
    "rank" integer NOT NULL,
    "retrieval_score" double precision NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "representation_id" "uuid",
    "content" "text",
    "document_id" "uuid" NOT NULL,
    "semantic_score" double precision,
    "lexical_score" double precision,
    "location" "jsonb"
);


ALTER TABLE "public"."retrieval_results" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."search_history" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "folder_id" "uuid",
    "query" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "investigation_id" "uuid"
);


ALTER TABLE "public"."search_history" OWNER TO "postgres";


ALTER TABLE ONLY "public"."chunks" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."chunks_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."chunks"
    ADD CONSTRAINT "chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_representations"
    ADD CONSTRAINT "document_representations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_folder_id_document_hash_key" UNIQUE ("folder_id", "document_hash");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."evidences"
    ADD CONSTRAINT "evidences_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."folders"
    ADD CONSTRAINT "folders_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."folders"
    ADD CONSTRAINT "folders_user_id_drive_id_key" UNIQUE ("user_id", "drive_id");



ALTER TABLE ONLY "public"."investigations"
    ADD CONSTRAINT "investigations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."jobs"
    ADD CONSTRAINT "jobs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."operations"
    ADD CONSTRAINT "operations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."retrieval_results"
    ADD CONSTRAINT "retrieval_results_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."search_history"
    ADD CONSTRAINT "search_history_pkey" PRIMARY KEY ("id");



CREATE INDEX "chunks_document_id_idx" ON "public"."chunks" USING "btree" ("document_id");



CREATE INDEX "chunks_fts_idx" ON "public"."chunks" USING "gin" ("fts");



CREATE INDEX "chunks_representation_id_idx" ON "public"."chunks" USING "btree" ("representation_id");



CREATE INDEX "document_representations_created_at_idx" ON "public"."document_representations" USING "btree" ("created_at");



CREATE INDEX "document_representations_document_id_idx" ON "public"."document_representations" USING "btree" ("document_id");



CREATE INDEX "document_representations_id_idx" ON "public"."document_representations" USING "btree" ("id");



CREATE INDEX "evidences_investigation_idx" ON "public"."evidences" USING "btree" ("investigation_id");



CREATE INDEX "evidences_unit_idx" ON "public"."evidences" USING "btree" ("unit_id");



CREATE INDEX "investigations_folder_id_idx" ON "public"."investigations" USING "btree" ("folder_id");



CREATE INDEX "operations_target_idx" ON "public"."operations" USING "btree" ("target_type", "target_id");



CREATE INDEX "retrieval_results_investigation_idx" ON "public"."retrieval_results" USING "btree" ("investigation_id", "rank");



CREATE INDEX "retrieval_results_representation_id_idx" ON "public"."retrieval_results" USING "btree" ("representation_id");



CREATE INDEX "retrieval_results_unit_idx" ON "public"."retrieval_results" USING "btree" ("unit_id");



CREATE INDEX "search_history_investigation_id_idx" ON "public"."search_history" USING "btree" ("investigation_id");



CREATE OR REPLACE TRIGGER "chunks_fts_trigger" BEFORE INSERT OR UPDATE OF "content" ON "public"."chunks" FOR EACH ROW EXECUTE FUNCTION "public"."chunks_update_fts"();



ALTER TABLE ONLY "public"."chunks"
    ADD CONSTRAINT "chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chunks"
    ADD CONSTRAINT "chunks_folder_id_fkey" FOREIGN KEY ("folder_id") REFERENCES "public"."folders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chunks"
    ADD CONSTRAINT "chunks_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_representations"
    ADD CONSTRAINT "document_representations_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_current_representation_id_fkey" FOREIGN KEY ("current_representation_id") REFERENCES "public"."document_representations"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_folder_id_fkey" FOREIGN KEY ("folder_id") REFERENCES "public"."folders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."evidences"
    ADD CONSTRAINT "evidences_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."evidences"
    ADD CONSTRAINT "evidences_investigation_id_fkey" FOREIGN KEY ("investigation_id") REFERENCES "public"."investigations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."evidences"
    ADD CONSTRAINT "evidences_unit_id_fkey" FOREIGN KEY ("unit_id") REFERENCES "public"."chunks"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."folders"
    ADD CONSTRAINT "folders_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."investigations"
    ADD CONSTRAINT "investigations_folder_id_fkey" FOREIGN KEY ("folder_id") REFERENCES "public"."folders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."investigations"
    ADD CONSTRAINT "investigations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."jobs"
    ADD CONSTRAINT "jobs_folder_id_fkey" FOREIGN KEY ("folder_id") REFERENCES "public"."folders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."jobs"
    ADD CONSTRAINT "jobs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."retrieval_results"
    ADD CONSTRAINT "retrieval_results_investigation_id_fkey" FOREIGN KEY ("investigation_id") REFERENCES "public"."investigations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."retrieval_results"
    ADD CONSTRAINT "retrieval_results_representation_id_fkey" FOREIGN KEY ("representation_id") REFERENCES "public"."document_representations"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."retrieval_results"
    ADD CONSTRAINT "retrieval_results_unit_id_fkey" FOREIGN KEY ("unit_id") REFERENCES "public"."chunks"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."search_history"
    ADD CONSTRAINT "search_history_folder_id_fkey" FOREIGN KEY ("folder_id") REFERENCES "public"."folders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."search_history"
    ADD CONSTRAINT "search_history_investigation_id_fkey" FOREIGN KEY ("investigation_id") REFERENCES "public"."investigations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."search_history"
    ADD CONSTRAINT "search_history_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



CREATE POLICY "Acesso ao próprio histórico" ON "public"."search_history" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Acesso aos próprios acervos" ON "public"."folders" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Acesso aos próprios chunks" ON "public"."chunks" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Acesso aos próprios documentos" ON "public"."documents" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Acesso aos próprios jobs" ON "public"."jobs" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Leitura pública do acervo GEPAFOR" ON "public"."folders" FOR SELECT USING (("id" = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::"uuid"));



CREATE POLICY "Leitura pública dos chunks GEPAFOR" ON "public"."chunks" FOR SELECT USING (("folder_id" = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::"uuid"));



CREATE POLICY "Leitura pública dos documentos GEPAFOR" ON "public"."documents" FOR SELECT USING (("folder_id" = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::"uuid"));



ALTER TABLE "public"."chunks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."document_representations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."evidences" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."folders" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."investigations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."jobs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."operations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."retrieval_results" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."search_history" ENABLE ROW LEVEL SECURITY;


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."chunks_update_fts"() TO "anon";
GRANT ALL ON FUNCTION "public"."chunks_update_fts"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."chunks_update_fts"() TO "service_role";



GRANT ALL ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."v3_hybrid_search"("p_query_text" "text", "p_query_embedding" "public"."vector", "p_match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."v3_hybrid_search"("p_query_text" "text", "p_query_embedding" "public"."vector", "p_match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."v3_hybrid_search"("p_query_text" "text", "p_query_embedding" "public"."vector", "p_match_count" integer, "p_user_id" "uuid", "p_folder_id" "uuid") TO "service_role";



GRANT ALL ON TABLE "public"."chunks" TO "anon";
GRANT ALL ON TABLE "public"."chunks" TO "authenticated";
GRANT ALL ON TABLE "public"."chunks" TO "service_role";



GRANT ALL ON SEQUENCE "public"."chunks_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."chunks_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."chunks_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."document_representations" TO "anon";
GRANT ALL ON TABLE "public"."document_representations" TO "authenticated";
GRANT ALL ON TABLE "public"."document_representations" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."evidences" TO "anon";
GRANT ALL ON TABLE "public"."evidences" TO "authenticated";
GRANT ALL ON TABLE "public"."evidences" TO "service_role";



GRANT ALL ON TABLE "public"."folders" TO "anon";
GRANT ALL ON TABLE "public"."folders" TO "authenticated";
GRANT ALL ON TABLE "public"."folders" TO "service_role";



GRANT ALL ON TABLE "public"."investigations" TO "anon";
GRANT ALL ON TABLE "public"."investigations" TO "authenticated";
GRANT ALL ON TABLE "public"."investigations" TO "service_role";



GRANT ALL ON TABLE "public"."jobs" TO "anon";
GRANT ALL ON TABLE "public"."jobs" TO "authenticated";
GRANT ALL ON TABLE "public"."jobs" TO "service_role";



GRANT ALL ON TABLE "public"."operations" TO "anon";
GRANT ALL ON TABLE "public"."operations" TO "authenticated";
GRANT ALL ON TABLE "public"."operations" TO "service_role";



GRANT ALL ON TABLE "public"."retrieval_results" TO "anon";
GRANT ALL ON TABLE "public"."retrieval_results" TO "authenticated";
GRANT ALL ON TABLE "public"."retrieval_results" TO "service_role";



GRANT ALL ON TABLE "public"."search_history" TO "anon";
GRANT ALL ON TABLE "public"."search_history" TO "authenticated";
GRANT ALL ON TABLE "public"."search_history" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";







