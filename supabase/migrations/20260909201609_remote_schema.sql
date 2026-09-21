SET local check_function_bodies = off;

CREATE EXTENSION "vector" SCHEMA "public";

CREATE SEQUENCE "public"."chunks_id_seq" AS bigint INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1 NO CYCLE;

CREATE TABLE "public"."chunks" (
  "id"          bigint             NOT NULL DEFAULT nextval('public.chunks_id_seq'::regclass),
  "user_id"     uuid,
  "folder_id"   uuid,
  "document_id" uuid,
  "content"     text               NOT NULL,
  "section"     text,
  "embedding"   public.vector(768),
  CONSTRAINT "chunks_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."chunks"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."documents" (
  "id"               uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "user_id"          uuid,
  "folder_id"        uuid,
  "title"            text                     NOT NULL,
  "authors"          text[],
  "publication_year" text,
  "document_hash"    text                     NOT NULL,
  "drive_link"       text,
  "drive_file_id"    text,
  "content"          text,
  "created_at"       timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  CONSTRAINT "documents_folder_id_document_hash_key" UNIQUE (folder_id, document_hash),
  CONSTRAINT "documents_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."documents"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."folders" (
  "id"         uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "user_id"    uuid,
  "name"       text                     NOT NULL,
  "drive_id"   text,
  "is_active"  boolean                  DEFAULT true,
  "created_at" timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  CONSTRAINT "folders_pkey" PRIMARY KEY (id),
  CONSTRAINT "folders_user_id_drive_id_key" UNIQUE (user_id, drive_id)
);

ALTER TABLE "public"."folders"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."jobs" (
  "id"            uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "user_id"       uuid,
  "folder_id"     uuid,
  "file_name"     text                     NOT NULL,
  "drive_file_id" text,
  "status"        text                     DEFAULT 'pending'::text,
  "error_log"     text,
  "created_at"    timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  "updated_at"    timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  "progress"      integer                  DEFAULT 0,
  CONSTRAINT "jobs_pkey" PRIMARY KEY (id),
  CONSTRAINT "jobs_status_check" CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text])))
);

ALTER TABLE "public"."jobs"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."search_history" (
  "id"         uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "user_id"    uuid,
  "folder_id"  uuid,
  "query"      text                     NOT NULL,
  "created_at" timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  CONSTRAINT "search_history_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."search_history"
  ENABLE ROW LEVEL SECURITY;

ALTER SEQUENCE "public"."chunks_id_seq" OWNED BY "public"."chunks"."id";

CREATE OR REPLACE FUNCTION public.match_chunks (
  query_embedding public.vector,
  match_threshold double precision,
  match_count     integer,
  p_user_id       uuid,
  p_folder_id     uuid
)
  RETURNS TABLE (
    id               bigint,
    document_id      uuid,
    content          text,
    section          text,
    similarity       double precision,
    title            text,
    authors          text[],
    publication_year text,
    drive_link       text
  )
  LANGUAGE plpgsql
  AS $function$
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
$function$;

ALTER TABLE "public"."chunks"
  ADD CONSTRAINT "chunks_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."chunks"
  ADD CONSTRAINT "chunks_document_id_fkey" FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

ALTER TABLE "public"."documents"
  ADD CONSTRAINT "documents_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."chunks"
  ADD CONSTRAINT "chunks_folder_id_fkey" FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;

ALTER TABLE "public"."documents"
  ADD CONSTRAINT "documents_folder_id_fkey" FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;

ALTER TABLE "public"."folders"
  ADD CONSTRAINT "folders_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."jobs"
  ADD CONSTRAINT "jobs_folder_id_fkey" FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;

ALTER TABLE "public"."jobs"
  ADD CONSTRAINT "jobs_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."search_history"
  ADD CONSTRAINT "search_history_folder_id_fkey" FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;

ALTER TABLE "public"."search_history"
  ADD CONSTRAINT "search_history_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE POLICY "Acesso aos próprios chunks" ON "public"."chunks"
  FOR ALL
  TO PUBLIC
  USING ((auth.uid() = user_id));

CREATE POLICY "Leitura pública dos chunks GEPAFOR" ON "public"."chunks"
  FOR SELECT
  TO PUBLIC
  USING ((folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::uuid));

CREATE POLICY "Acesso aos próprios documentos" ON "public"."documents"
  FOR ALL
  TO PUBLIC
  USING ((auth.uid() = user_id));

CREATE POLICY "Leitura pública dos documentos GEPAFOR" ON "public"."documents"
  FOR SELECT
  TO PUBLIC
  USING ((folder_id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::uuid));

CREATE POLICY "Acesso aos próprios acervos" ON "public"."folders"
  FOR ALL
  TO PUBLIC
  USING ((auth.uid() = user_id));

CREATE POLICY "Leitura pública do acervo GEPAFOR" ON "public"."folders"
  FOR SELECT
  TO PUBLIC
  USING ((id = 'f7faf7d9-ec80-46c6-9572-174865bf1e62'::uuid));

CREATE POLICY "Acesso aos próprios jobs" ON "public"."jobs"
  FOR ALL
  TO PUBLIC
  USING ((auth.uid() = user_id));

CREATE POLICY "Acesso ao próprio histórico" ON "public"."search_history"
  FOR ALL
  TO PUBLIC
  USING ((auth.uid() = user_id));

ALTER PUBLICATION "supabase_realtime" ADD TABLE "public"."jobs";

COMMENT ON EXTENSION "vector" IS 'vector data type and ivfflat and hnsw access methods';

GRANT EXECUTE ON FUNCTION "public"."match_chunks"(public.vector, double precision, integer, uuid, uuid) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT SELECT, UPDATE, USAGE ON SEQUENCE "public"."chunks_id_seq" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."chunks" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."documents" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."folders" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."jobs" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."search_history" TO "anon", "authenticated", "postgres", "service_role";

