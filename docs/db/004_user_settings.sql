-- User settings persistence (run once in Supabase SQL editor)

create table if not exists public.user_settings (
  user_id uuid primary key,
  notifications_enabled boolean not null default true,
  days_before_deadline integer not null default 3,
  timezone varchar(60),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

