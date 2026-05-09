'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { BackendError, completeGoogleCalendarOAuth } from '@/lib/backend';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';

export default function GoogleCallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'working' | 'ok' | 'error'>('working');
  const [message, setMessage] = useState<string | null>(null);
  const ranRef = useRef(false);

  useEffect(() => {
    // Next dev + React StrictMode can run effects twice; avoid double token exchange.
    if (ranRef.current) return;
    ranRef.current = true;

    const err = searchParams.get('error');
    const desc = searchParams.get('error_description');
    if (err) {
      setStatus('error');
      setMessage(
        desc ? `Google sign-in was cancelled or failed: ${desc}` : 'Google sign-in was cancelled or failed.'
      );
      return;
    }

    const code = searchParams.get('code');
    if (!code) {
      setStatus('error');
      setMessage('Missing authorization code. Start again from Classes.');
      return;
    }
    const state = searchParams.get('state');
    const verifier =
      state ? sessionStorage.getItem(`gp_google_oauth_verifier:${state}`) : null;
    if (state && verifier) {
      sessionStorage.removeItem(`gp_google_oauth_verifier:${state}`);
    }

    let cancelled = false;
    (async () => {
      try {
        await completeGoogleCalendarOAuth(code, state, verifier);
        if (cancelled) return;
        setStatus('ok');
        setMessage(null);
        router.replace('/classes');
      } catch (e: unknown) {
        if (cancelled) return;
        setStatus('error');
        if (e instanceof BackendError) {
          setMessage(e.message);
        } else {
          setMessage(e instanceof Error ? e.message : 'Could not complete Google connection.');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, router]);

  return (
    <StudyPlanShell
      title="Google Calendar"
      subtitle="Finishing connection…"
      actions={
        <Link href="/classes" className="text-sm text-slate-300 hover:text-white transition-colors">
          Back to Classes
        </Link>
      }
    >
      {status === 'working' ? (
        <div className="text-sm text-slate-300">Connecting your Google account…</div>
      ) : null}
      {status === 'ok' ? (
        <div className="text-sm text-emerald-300">Connected. Redirecting to Classes…</div>
      ) : null}
      {status === 'error' && message ? (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100 space-y-3">
          <div>{message}</div>
          <Link
            href="/classes"
            className="inline-block rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold"
          >
            Back to Classes
          </Link>
        </div>
      ) : null}
    </StudyPlanShell>
  );
}
