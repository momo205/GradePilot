-- Per-class lecture meeting pattern (used by focused study session scheduler
-- to compute the next-lecture anchor).
-- Idempotent: safe to run multiple times.

alter table if exists public.classes
  add column if not exists meeting_pattern jsonb;
