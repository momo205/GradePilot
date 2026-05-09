'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  BackendError,
  getUserSettings,
  listClasses,
  startGoogleCalendarOAuth,
  type ClassOut,
} from '@/lib/backend';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';
import { createClient } from '@/lib/supabase/client';

export default function ClassesIndexClient() {
  const supabase = createClient();
  const [classes, setClasses] = useState<ClassOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [googleConnected, setGoogleConnected] = useState<boolean | null>(null);
  const [googleConnectBusy, setGoogleConnectBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        const [res, settings] = await Promise.all([listClasses(), getUserSettings()]);
        if (cancelled) return;
        setClasses(res);
        setGoogleConnected(settings.googleConnected);
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

