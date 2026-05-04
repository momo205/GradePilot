-- Chat tables for GradePilot (run once in Supabase SQL editor)
-- Mirrors SQLAlchemy models in app/db/models.py (ChatSession, ChatMessage, ChatState).

create table if not exists public.chat_sessions (
  id uuid primary key,
  user_id uuid not null,
  status varchar(50) not null default 'active',
  created_at timestamptz not null default now()
);

create index if not exists ix_chat_sessions_user_id on public.chat_sessions (user_id);

create table if not exists public.chat_messages (
  id uuid primary key,
  session_id uuid not null references public.chat_sessions (id) on delete cascade,
  user_id uuid not null,
  role varchar(20) not null,
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists ix_chat_messages_session_id on public.chat_messages (session_id);
create index if not exists ix_chat_messages_user_id on public.chat_messages (user_id);

-- One row per session. The PK is the session_id (matches the SQLAlchemy model).
create table if not exists public.chat_state (
  session_id uuid primary key references public.chat_sessions (id) on delete cascade,
  user_id uuid not null,
  state_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists ix_chat_state_user_id on public.chat_state (user_id);

