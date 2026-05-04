-- RAG schema helpers for Supabase Postgres
--
-- Run in order:
--   1) This file (extension)
--   2) 002_rag_documents.sql (creates documents + document_chunks tables)

create extension if not exists vector;

-- Recommended indexes (adjust to match your actual workload).
-- B-tree indexes are already declared in SQLAlchemy for common filters.

-- Vector index: choose ONE depending on what your Supabase Postgres supports.
-- ivfflat is widely available, but requires ANALYZE and tuning 'lists'.
-- hnsw (if available) often performs better without as much tuning.

-- IVFFLAT example:
-- create index if not exists ix_document_chunks_embedding_ivfflat
-- on public.document_chunks
-- using ivfflat (embedding vector_cosine_ops)
-- with (lists = 100);

-- HNSW example:
-- create index if not exists ix_document_chunks_embedding_hnsw
-- on public.document_chunks
-- using hnsw (embedding vector_cosine_ops);

-- After creating IVFFLAT, run:
-- analyze public.document_chunks;

