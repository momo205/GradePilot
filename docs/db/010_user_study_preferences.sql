-- Per-user preferences that drive the focused study session scheduler:
--   * preferred_study_windows: list of {start, end} HH:MM windows (user local
--     time) where the scheduler is allowed to place sessions.
--   * auto_schedule_sessions: whether the replanner should auto-create
--     calendar events on notes_added.
-- Idempotent: safe to run multiple times.

alter table if exists public.user_settings
  add column if not exists preferred_study_windows jsonb not null default '[]'::jsonb,
  add column if not exists auto_schedule_sessions boolean not null default false;
