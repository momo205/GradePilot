-- Google OAuth + calendar sync tables (run once in Supabase SQL editor)

create table if not exists public.user_integrations_google (
  user_id uuid primary key,
  refresh_token text not null,
  access_token text,
  token_expiry timestamptz,
  scopes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.calendar_event_links (
  id uuid primary key,
  user_id uuid not null,
  class_id uuid not null references public.classes (id) on delete cascade,
  kind varchar(30) not null,
  local_id varchar(200) not null,
  google_calendar_id varchar(200) not null,
  google_event_id varchar(200) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_calendar_event_links_user_id on public.calendar_event_links (user_id);
create index if not exists ix_calendar_event_links_class_id on public.calendar_event_links (class_id);
create unique index if not exists ix_calendar_event_links_user_kind_local
  on public.calendar_event_links (user_id, kind, local_id);

