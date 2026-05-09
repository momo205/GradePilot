-- Repair: remove LangGraph checkpoint objects from the old shallow-schema 007
-- (missing checkpoints.checkpoint_id, wrong checkpoint_blobs primary key, etc.).
-- After this, run docs/db/007_langgraph_checkpoints.sql again, then restart the API so
-- PostgresSaver.setup() can populate checkpoint_migrations.

drop table if exists public.checkpoint_writes cascade;
drop table if exists public.checkpoint_blobs cascade;
drop table if exists public.checkpoints cascade;
drop table if exists public.checkpoint_migrations cascade;
