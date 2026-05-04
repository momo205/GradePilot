'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { listClasses, type ClassOut } from '@/lib/backend';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';
import { createClient } from '@/lib/supabase/client';

export default function ClassesIndexClient() {
  const supabase = createClient();
  const [classes, setClasses] = useState<ClassOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        const res = await listClasses();
        if (cancelled) return;
        setClasses(res);
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load classes');
        setClasses([]);
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
          <Link href="/chat" className="text-sm text-slate-300 hover:text-white transition-colors">
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

      {classes === null ? (
        <div className="text-sm text-slate-300">Loading…</div>
      ) : classes.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="text-sm font-semibold text-white">No classes yet</div>
          <div className="mt-2 text-sm text-slate-300">
            Start onboarding to add your first class.
          </div>
          <div className="mt-4">
            <Link href="/chat" className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold">
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

