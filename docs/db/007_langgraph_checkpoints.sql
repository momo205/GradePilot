-- LangGraph Postgres checkpointer tables for PostgresSaver (langgraph-checkpoint-postgres 3.x).
-- Matches langgraph.checkpoint.postgres.base.MIGRATIONS final shape (not ShallowPostgresSaver).
--
-- After applying, the first app run will call PostgresSaver.setup() to record migration versions.
-- Do NOT manually insert into checkpoint_migrations; let setup() own version rows.
--
-- If you previously applied an older 007 (shallow schema without checkpoints.checkpoint_id),
-- run 008_langgraph_checkpoints_repair.sql first, then this file.

create table if not exists public.checkpoint_migrations (
  v integer primary key
);

create table if not exists public.checkpoints (
  thread_id text not null,
  checkpoint_ns text not null default '',
  checkpoint_id text not null,
  parent_checkpoint_id text,
  type text,
  checkpoint jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  primary key (thread_id, checkpoint_ns, checkpoint_id)
);

create table if not exists public.checkpoint_blobs (
  thread_id text not null,
  checkpoint_ns text not null default '',
  channel text not null,
  version text not null,
  type text not null,
  blob bytea,
  primary key (thread_id, checkpoint_ns, channel, version)
);

create table if not exists public.checkpoint_writes (
  thread_id text not null,
  checkpoint_ns text not null default '',
  checkpoint_id text not null,
  task_id text not null,
  idx integer not null,
  channel text not null,
  type text,
  blob bytea not null,
  task_path text not null default '',
  primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

create index if not exists checkpoints_thread_id_idx
  on public.checkpoints(thread_id);

create index if not exists checkpoint_blobs_thread_id_idx
  on public.checkpoint_blobs(thread_id);

create index if not exists checkpoint_writes_thread_id_idx
  on public.checkpoint_writes(thread_id);
