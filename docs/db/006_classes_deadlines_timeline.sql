-- Add per-class semester timeline fields + deadline completion support.
-- Run once in Supabase SQL editor AFTER your base tables exist (public.classes, public.deadlines).

alter table if exists public.classes
  add column if not exists semester_start varchar(40),
  add column if not exists semester_end varchar(40),
  add column if not exists timezone varchar(60),
  add column if not exists availability_json jsonb;

alter table if exists public.deadlines
  add column if not exists completed_at timestamptz;

