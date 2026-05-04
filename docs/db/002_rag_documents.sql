-- RAG tables for GradePilot (run once in Supabase SQL editor)
-- Requires: public.classes already exists (same schema as SQLAlchemy models).

create extension if not exists vector;

create table if not exists public.documents (
  id uuid primary key,
  class_id uuid not null references public.classes (id) on delete cascade,
  user_id uuid not null,
  filename varchar(255) not null,
  title varchar(255),
  document_type varchar(50) not null default 'notes',
  raw_text text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ix_documents_class_id on public.documents (class_id);
create index if not exists ix_documents_user_id on public.documents (user_id);

-- gemini-embedding-001 is configured to return 768 dims (matches app/db/models.py Vector(768))
create table if not exists public.document_chunks (
  id uuid primary key,
  document_id uuid not null references public.documents (id) on delete cascade,
  class_id uuid not null references public.classes (id) on delete cascade,
  user_id uuid not null,
  chunk_index integer not null,
  chunk_text text not null,
  embedding vector(768) not null,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ix_document_chunks_document_id on public.document_chunks (document_id);
create index if not exists ix_document_chunks_user_class on public.document_chunks (user_id, class_id);
create index if not exists ix_document_chunks_document_chunk_index
  on public.document_chunks (document_id, chunk_index);
