'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  BackendError,
  getUserSettings,
  listClasses,
  startGoogleCalendarOAuth,
  updateUserSettings,
  type ClassOut,
} from '@/lib/backend';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';
import { createClient } from '@/lib/supabase/client';
import {
  HHMM_RE,
  MAX_STUDY_WINDOWS,
  StudyWindow,
  isValidStudyWindow,
} from '@/lib/settingsTypes';

export default function ClassesIndexClient() {
  const supabase = createClient();
  const [classes, setClasses] = useState<ClassOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [googleConnected, setGoogleConnected] = useState<boolean | null>(null);
  const [googleConnectBusy, setGoogleConnectBusy] = useState(false);

  const [autoSchedule, setAutoSchedule] = useState<boolean>(false);
  const [windows, setWindows] = useState<StudyWindow[]>([]);
  const [savingSchedulingPrefs, setSavingSchedulingPrefs] = useState(false);
  const [schedulingHint, setSchedulingHint] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        const [res, settings] = await Promise.all([listClasses(), getUserSettings()]);
        if (cancelled) return;
        setClasses(res);
        setGoogleConnected(settings.googleConnected);
        setAutoSchedule(Boolean(settings.autoScheduleSessions));
        setWindows(settings.preferredStudyWindows ?? []);
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load classes');
        setClasses([]);
        setGoogleConnected(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function persistSchedulingPrefs(next: {
    autoScheduleSessions?: boolean;
    preferredStudyWindows?: StudyWindow[];
  }): Promise<void> {
    setSavingSchedulingPrefs(true);
    setSchedulingHint(null);
    setError(null);
    try {
      const updated = await updateUserSettings(next);
      setAutoSchedule(Boolean(updated.autoScheduleSessions));
      setWindows(updated.preferredStudyWindows ?? []);
      setSchedulingHint('Saved.');
    } catch (e: unknown) {
      setError(
        e instanceof BackendError
          ? e.message
          : e instanceof Error
            ? e.message
            : 'Failed to save scheduling preferences'
      );
    } finally {
      setSavingSchedulingPrefs(false);
    }
  }

  return (
    <StudyPlanShell
      title="Classes"
      subtitle="Your current classes. Add a new one via the onboarding chat."
      actions={
        <div className="flex items-center gap-4">
          <Link
            href="/chat?new=1"
            className="text-sm text-slate-300 hover:text-white transition-colors"
          >
            Add New Class
          </Link>
          <button
            onClick={async () => {
              await supabase.auth.signOut();
              window.location.href = '/';
            }}
            className="text-sm text-slate-300 hover:text-white transition-colors"
          >
            Sign out
          </button>
        </div>
      }
    >
      {error ? (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 mb-6">
        <div className="text-sm font-semibold text-white">Google Calendar</div>
        <p className="mt-1 text-sm text-slate-300">
          Sync class deadlines to a calendar named &quot;GradePilot&quot; in your Google account.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {googleConnected === null ? (
            <span className="text-xs text-slate-400">Checking connection…</span>
          ) : googleConnected ? (
            <span className="text-xs font-medium text-emerald-400">Connected</span>
          ) : (
            <button
              type="button"
              disabled={googleConnectBusy}
              onClick={async () => {
                setGoogleConnectBusy(true);
                setError(null);
                try {
                      const { authorization_url, state, code_verifier } =
                        await startGoogleCalendarOAuth();
                      if (state && code_verifier) {
                        sessionStorage.setItem(
                          `gp_google_oauth_verifier:${state}`,
                          code_verifier
                        );
                      }
                  window.location.assign(authorization_url);
                } catch (e: unknown) {
                  const msg =
                    e instanceof BackendError
                      ? e.message
                      : e instanceof Error
                        ? e.message
                        : 'Could not start Google sign-in';
                  setError(msg);
                  setGoogleConnectBusy(false);
                }
              }}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              {googleConnectBusy ? 'Redirecting…' : 'Connect Google Calendar'}
            </button>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-white">
              Smart study sessions
            </div>
            <p className="mt-1 text-sm text-slate-300 max-w-xl">
              When you upload notes, GradePilot can find a 60-minute slot in
              your Google Calendar before your next lecture or deadline and
              book it on the &quot;GradePilot&quot; calendar.
            </p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-white">
            <input
              type="checkbox"
              checked={autoSchedule}
              disabled={savingSchedulingPrefs || googleConnected !== true}
              onChange={(e) =>
                persistSchedulingPrefs({ autoScheduleSessions: e.target.checked })
              }
            />
            Auto-schedule on new notes
          </label>
        </div>

        {googleConnected !== true ? (
          <p className="mt-3 text-xs text-amber-200/90">
            Connect Google Calendar above to enable smart scheduling.
          </p>
        ) : null}

        <div className="mt-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Preferred study windows
          </div>
          <p className="mt-1 text-xs text-slate-400">
            We&apos;ll try to land sessions inside one of these (your local
            time, max {MAX_STUDY_WINDOWS}). If everything is busy, we&apos;ll
            still book the next free slot but mark it as outside your
            preferred time.
          </p>

          <div className="mt-3 space-y-2">
            {windows.length === 0 ? (
              <div className="text-xs text-slate-400">
                No preferred windows yet — sessions will land at the first free
                slot.
              </div>
            ) : (
              windows.map((w, idx) => {
                const valid = isValidStudyWindow(w);
                return (
                  <div
                    key={idx}
                    className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                  >
                    <span className="text-xs text-slate-300">From</span>
                    <input
                      value={w.start}
                      onChange={(e) => {
                        const next = windows.slice();
                        next[idx] = { ...w, start: e.target.value };
                        setWindows(next);
                      }}
                      placeholder="07:00"
                      className="w-20 bg-black/40 border border-white/10 rounded-lg px-2 py-1 text-sm text-white"
                    />
                    <span className="text-xs text-slate-300">to</span>
                    <input
                      value={w.end}
                      onChange={(e) => {
                        const next = windows.slice();
                        next[idx] = { ...w, end: e.target.value };
                        setWindows(next);
                      }}
                      placeholder="10:00"
                      className="w-20 bg-black/40 border border-white/10 rounded-lg px-2 py-1 text-sm text-white"
                    />
                    {!valid && (HHMM_RE.test(w.start) || w.start === '') ? (
                      <span className="text-xs text-rose-300">
                        Use HH:MM and start &lt; end
                      </span>
                    ) : null}
                    <button
                      type="button"
                      className="ml-auto text-xs text-slate-300 hover:text-white"
                      onClick={() =>
                        setWindows(windows.filter((_, i) => i !== idx))
                      }
                    >
                      Remove
                    </button>
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={
                savingSchedulingPrefs || windows.length >= MAX_STUDY_WINDOWS
              }
              onClick={() =>
                setWindows([...windows, { start: '19:00', end: '23:00' }])
              }
              className="rounded-xl border border-white/20 bg-white/[0.06] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              + Add window
            </button>
            <button
              type="button"
              disabled={
                savingSchedulingPrefs || !windows.every(isValidStudyWindow)
              }
              onClick={() =>
                persistSchedulingPrefs({ preferredStudyWindows: windows })
              }
              className="rounded-xl bg-white text-black px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
            >
              {savingSchedulingPrefs ? 'Saving…' : 'Save windows'}
            </button>
            {schedulingHint ? (
              <span className="text-xs text-emerald-400">{schedulingHint}</span>
            ) : null}
          </div>
        </div>
      </div>

      {classes === null ? (
        <div className="text-sm text-slate-300">Loading…</div>
      ) : classes.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="text-sm font-semibold text-white">No classes yet</div>
          <div className="mt-2 text-sm text-slate-300">
            Start onboarding to add your first class.
          </div>
          <div className="mt-4">
            <Link
              href="/chat?new=1"
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold"
            >
              Start onboarding
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {classes.map((c) => (
            <Link
              key={c.id}
              href={`/classes/${c.id}`}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 hover:bg-white/[0.06] transition-colors"
            >
              <div className="text-sm font-semibold text-white">{c.title}</div>
              <div className="mt-2 text-xs text-slate-400">
                Created {new Date(c.created_at).toLocaleDateString()}
              </div>
            </Link>
          ))}
        </div>
      )}
    </StudyPlanShell>
  );
}

