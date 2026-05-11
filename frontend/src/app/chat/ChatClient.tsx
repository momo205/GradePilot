'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  createOrGetChatSession,
  getChatSession,
  sendChatMessage,
  uploadOnboardingSyllabus,
  type ChatReplyOut,
  type ChatToolAction,
  type SyllabusOnboardingOut,
} from '@/lib/backend';
import { createClient } from '@/lib/supabase/client';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';

type ToolCard = { title: string; detail?: string };

type TermChoice = 'from_syllabus' | 'fall' | 'spring';

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function inferCalendarYear(start: string, end: string): number {
  for (const d of [start, end]) {
    if (d && ISO_DATE.test(d)) return parseInt(d.slice(0, 4), 10);
  }
  return new Date().getFullYear();
}

function fallDefaults(y: number) {
  return { start: `${y}-08-01`, end: `${y}-12-20` };
}

function springDefaults(y: number) {
  return { start: `${y}-01-01`, end: `${y}-06-30` };
}

function normalizeTerm(v: unknown): 'fall' | 'spring' | null {
  if (v === 'fall' || v === 'spring') return v;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    if (s === 'fall' || s === 'autumn') return 'fall';
    if (s === 'spring') return 'spring';
  }
  return null;
}

function toolActionToCard(a: ChatToolAction): ToolCard | null {
  if (a.type === 'create_class') {
    const p = a.payload as Record<string, unknown>;
    const title = typeof p.title === 'string' ? p.title : String(p.title ?? '');
    return { title: 'Created class', detail: title };
  }
  return { title: `Action: ${a.type}` };
}

export default function ChatClient() {
  const supabase = createClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syllabusBusy, setSyllabusBusy] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatReplyOut | null>(null);
  const [toolCards, setToolCards] = useState<ToolCard[]>([]);

  const [syllabusSnapshot, setSyllabusSnapshot] = useState<{
    timezone?: string;
    start?: string;
    end?: string;
    term?: 'fall' | 'spring' | null;
  } | null>(null);
  const [termChoice, setTermChoice] = useState<TermChoice>('fall');

  const rawPhase = chat?.state?.phase;
  const phaseNum =
    typeof rawPhase === 'number'
      ? rawPhase
      : typeof rawPhase === 'string'
        ? Number(rawPhase) || 1
        : 1;
  const phase = phaseNum > 4 ? 4 : phaseNum;

  const classId = useMemo(() => {
    const direct = chat?.class_id;
    if (typeof direct === 'string' && direct) return direct;
    const fromState = chat?.state?.class_id;
    if (typeof fromState === 'string' && fromState) return fromState;
    return null;
  }, [chat]);

  const importedDeadlineCount = useMemo(() => {
    const n = chat?.state?.deadlines_imported_count;
    return typeof n === 'number' ? n : typeof n === 'string' ? Number(n) || 0 : 0;
  }, [chat?.state?.deadlines_imported_count]);

  const inferredTermFromState = useMemo(
    () => normalizeTerm(chat?.state?.suggested_semester_term),
    [chat?.state?.suggested_semester_term]
  );

  const [classTitle, setClassTitle] = useState('');
  const [timezone, setTimezone] = useState('America/New_York');
  const [semesterStart, setSemesterStart] = useState('');
  const [semesterEnd, setSemesterEnd] = useState('');

  const timelineHydratedKey = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const forceNew =
          searchParams?.get('new') === '1' || searchParams?.get('new') === 'true';
        const sess = await createOrGetChatSession({ forceNew });
        if (cancelled) return;
        setSessionId(sess.id);
        const reply = await getChatSession(sess.id);
        if (cancelled) return;
        setChat(reply);
        setToolCards([]);
        timelineHydratedKey.current = null;
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load chat');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  useEffect(() => {
    if (chat?.complete && chat.class_id) {
      router.push(`/classes/${chat.class_id}`);
    }
  }, [chat?.complete, chat?.class_id, router]);

  // Hydrate timeline fields when opening phase 3 from saved chat state (reload).
  useEffect(() => {
    if (phase !== 3 || !sessionId) return;
    const st = chat?.state;
    if (!st || typeof st !== 'object') return;
    const key = `${sessionId}:${String(st.phase)}`;
    if (timelineHydratedKey.current === key) return;

    const tz =
      (typeof st.suggested_timezone === 'string' && st.suggested_timezone.trim()) ||
      (typeof st.timezone === 'string' && st.timezone.trim()) ||
      '';
    const ss =
      (typeof st.suggested_semester_start === 'string' && st.suggested_semester_start.trim()) ||
      (typeof st.semester_start === 'string' && st.semester_start.trim()) ||
      '';
    const se =
      (typeof st.suggested_semester_end === 'string' && st.suggested_semester_end.trim()) ||
      (typeof st.semester_end === 'string' && st.semester_end.trim()) ||
      '';
    const term = normalizeTerm(st.suggested_semester_term);
    if (tz) setTimezone(tz);
    if (ss) setSemesterStart(ss);
    if (se) setSemesterEnd(se);
    if (ss && se) {
      setSyllabusSnapshot({
        timezone: tz || undefined,
        start: ss,
        end: se,
        term: term ?? undefined,
      });
      setTermChoice('from_syllabus');
    }
    timelineHydratedKey.current = key;
  }, [phase, sessionId, chat?.state]);

  function applyTermChoice(choice: TermChoice, snap: typeof syllabusSnapshot) {
    const y =
      snap?.start && ISO_DATE.test(snap.start)
        ? inferCalendarYear(snap.start, snap.end ?? '')
        : inferCalendarYear(semesterStart, semesterEnd);
    if (choice === 'from_syllabus' && snap?.start && snap.end) {
      if (snap.timezone) setTimezone(snap.timezone);
      setSemesterStart(snap.start);
      setSemesterEnd(snap.end);
      return;
    }
    if (choice === 'fall') {
      const d = fallDefaults(y);
      setSemesterStart(d.start);
      setSemesterEnd(d.end);
      return;
    }
    if (choice === 'spring') {
      const d = springDefaults(y);
      setSemesterStart(d.start);
      setSemesterEnd(d.end);
    }
  }

  function onSyllabusProcessed(out: SyllabusOnboardingOut) {
    const snap = {
      timezone: out.suggested_timezone ?? undefined,
      start: out.suggested_semester_start ?? undefined,
      end: out.suggested_semester_end ?? undefined,
      term: normalizeTerm(out.suggested_semester_term),
    };
    setSyllabusSnapshot(snap);
    if (out.suggested_timezone) setTimezone(out.suggested_timezone);
    if (out.suggested_semester_start) setSemesterStart(out.suggested_semester_start);
    if (out.suggested_semester_end) setSemesterEnd(out.suggested_semester_end);

    const hasFullDates = Boolean(out.suggested_semester_start && out.suggested_semester_end);
    if (hasFullDates) {
      setTermChoice('from_syllabus');
    } else {
      const t = normalizeTerm(out.suggested_semester_term);
      const y = inferCalendarYear(
        out.suggested_semester_start ?? '',
        out.suggested_semester_end ?? ''
      );
      if (t === 'spring') {
        setTermChoice('spring');
        const d = springDefaults(y);
        setSemesterStart(d.start);
        setSemesterEnd(d.end);
      } else {
        setTermChoice('fall');
        const d = fallDefaults(y);
        setSemesterStart(d.start);
        setSemesterEnd(d.end);
      }
    }
    timelineHydratedKey.current = null;
  }

  async function sendRaw(content: string) {
    if (!sessionId) return;
    const c = content.trim();
    if (!c) return;
    setLoading(true);
    setError(null);
    try {
      const out = await sendChatMessage(sessionId, c);
      setChat(out);
      const newCards = (out.tool_actions ?? [])
        .map(toolActionToCard)
        .filter((c): c is ToolCard => Boolean(c));
      setToolCards((prev) => [...newCards, ...prev].slice(0, 12));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  }

  const termHint =
    inferredTermFromState === 'fall' || inferredTermFromState === 'spring' ? (
      <>
        From your syllabus we inferred{' '}
        <strong>{inferredTermFromState === 'fall' ? 'Fall' : 'Spring'}</strong>
      </>
    ) : (
      <>
        We could not clearly infer Fall vs Spring from the syllabus — pick one for default dates
        (you can still edit).
      </>
    );

  return (
    <StudyPlanShell
      title="GradePilot Chat"
      subtitle="A step-by-step setup wizard for one class."
      actions={
        <div className="flex items-center gap-4">
          <Link href="/classes" className="text-sm text-slate-300 hover:text-white transition-colors">
            Classes
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
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <aside className="lg:col-span-4 space-y-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-sm font-semibold">Status</div>
            <div className="mt-2 text-sm text-slate-300">
              Phase: <span className="text-white">{phase}</span> / 4
            </div>
            {classId ? (
              <div className="mt-2 text-xs text-slate-400">
                class_id: <span className="font-mono text-slate-200">{classId}</span>
              </div>
            ) : null}
          </div>

          {toolCards.length ? (
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
              <div className="text-sm font-semibold">Recent actions</div>
              <ul className="space-y-2">
                {toolCards.map((c, i) => (
                  <li key={`${c.title}-${i}`} className="text-xs text-slate-300 border-l-2 border-white/20 pl-3">
                    <div className="text-slate-100">{c.title}</div>
                    {c.detail ? <div className="text-slate-400 mt-0.5">{c.detail}</div> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </aside>

        <main className="lg:col-span-8 space-y-4">
          {error ? (
            <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
            <div className="space-y-3 max-h-[55vh] overflow-auto pr-1">
              {(chat?.messages ?? []).length ? (
                chat!.messages.map((m) => (
                  <div
                    key={m.id}
                    className={[
                      'rounded-xl border border-white/10 p-3 text-sm whitespace-pre-wrap',
                      m.role === 'assistant' ? 'bg-black/20 text-slate-100' : 'bg-white/[0.04] text-white',
                    ].join(' ')}
                  >
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-400 mb-2">
                      {m.role}
                    </div>
                    {m.content}
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-300">
                  Loading your onboarding wizard…
                </div>
              )}
            </div>

            {phase === 1 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-3">
                <div className="text-sm font-semibold text-white">Phase 1 — Class setup</div>
                <input
                  value={classTitle}
                  onChange={(e) => setClassTitle(e.target.value)}
                  placeholder='e.g. "CS 301 — Algorithms"'
                  className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                />
                <div className="flex justify-end">
                  <button
                    disabled={loading || classTitle.trim().length === 0}
                    onClick={() =>
                      void sendRaw(JSON.stringify({ class_title: classTitle.trim() }))
                    }
                    className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
                  >
                    Create class
                  </button>
                </div>
              </div>
            ) : null}

            {phase === 2 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-3">
                <div className="text-sm font-semibold text-white">Phase 2 — Syllabus</div>
                <p className="text-xs text-slate-400">
                  One upload: we read the PDF, extract deadlines, infer Fall/Spring when possible,
                  suggest term dates, add a course summary for Q&amp;A, and index the full syllabus.
                  This can take a minute — stay on this page until it finishes.
                </p>
                {syllabusBusy ? (
                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                    {syllabusBusy}
                  </div>
                ) : null}
                <label className="text-sm text-slate-300 hover:text-white cursor-pointer rounded-xl border border-white/15 bg-white/[0.03] px-4 py-2 inline-block">
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    disabled={loading || syllabusBusy !== null || !classId || !sessionId}
                    onChange={async (e) => {
                      const f = e.target.files?.[0];
                      e.target.value = '';
                      if (!f || !classId || !sessionId) return;
                      setError(null);
                      setSyllabusBusy(
                        'Processing syllabus: extracting text, running AI, building search index…'
                      );
                      try {
                        const out = await uploadOnboardingSyllabus(classId, f, sessionId);
                        onSyllabusProcessed(out);
                        setToolCards((prev) => [
                          {
                            title: 'Syllabus processed',
                            detail: `${out.deadlines_created} deadlines · ${out.syllabus_chunks} syllabus chunks · ${out.course_summary_chunks} summary chunks`,
                          },
                          ...prev,
                        ]);
                        const reply = await getChatSession(sessionId);
                        setChat(reply);
                      } catch (err: unknown) {
                        setError(err instanceof Error ? err.message : 'Syllabus processing failed');
                      } finally {
                        setSyllabusBusy(null);
                      }
                    }}
                  />
                  Upload syllabus PDF
                </label>
              </div>
            ) : null}

            {phase === 3 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-4">
                <div className="text-sm font-semibold text-white">Phase 3 — Semester timeline</div>
                <p className="text-xs text-slate-300 leading-relaxed">{termHint}</p>
                {importedDeadlineCount > 0 ? (
                  <p className="text-xs text-emerald-300/90">
                    Imported <span className="font-mono">{importedDeadlineCount}</span> deadline
                    {importedDeadlineCount === 1 ? '' : 's'} from your syllabus.
                  </p>
                ) : (
                  <p className="text-xs text-slate-400">
                    No deadlines were auto-detected — you can add them later from your class page.
                  </p>
                )}

                <div className="space-y-2 rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Term
                  </div>
                  <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name="term"
                      checked={termChoice === 'from_syllabus'}
                      disabled={!syllabusSnapshot?.start || !syllabusSnapshot?.end}
                      onChange={() => {
                        setTermChoice('from_syllabus');
                        applyTermChoice('from_syllabus', syllabusSnapshot);
                      }}
                    />
                    Use dates from syllabus
                    {syllabusSnapshot?.start && syllabusSnapshot?.end ? (
                      <span className="text-xs text-slate-500">
                        ({syllabusSnapshot.start} → {syllabusSnapshot.end})
                      </span>
                    ) : (
                      <span className="text-xs text-slate-500">(not available)</span>
                    )}
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name="term"
                      checked={termChoice === 'fall'}
                      onChange={() => {
                        setTermChoice('fall');
                        applyTermChoice('fall', syllabusSnapshot);
                      }}
                    />
                    Fall — default Aug 1 → Dec 20
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name="term"
                      checked={termChoice === 'spring'}
                      onChange={() => {
                        setTermChoice('spring');
                        applyTermChoice('spring', syllabusSnapshot);
                      }}
                    />
                    Spring — default Jan 1 → Jun 30
                  </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <input
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    placeholder="Timezone (e.g. America/New_York)"
                    className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                  <input
                    value={semesterStart}
                    onChange={(e) => setSemesterStart(e.target.value)}
                    placeholder="Start (YYYY-MM-DD)"
                    className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                  <input
                    value={semesterEnd}
                    onChange={(e) => setSemesterEnd(e.target.value)}
                    placeholder="End (YYYY-MM-DD)"
                    className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    disabled={
                      loading ||
                      !timezone.trim() ||
                      !semesterStart.trim() ||
                      !semesterEnd.trim()
                    }
                    onClick={() =>
                      void sendRaw(
                        JSON.stringify({
                          timezone: timezone.trim(),
                          semester_start: semesterStart.trim(),
                          semester_end: semesterEnd.trim(),
                        })
                      )
                    }
                    className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
                  >
                    Save &amp; generate plan
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  Upload readings, lecture notes, or slides later from your class dashboard.
                </p>
              </div>
            ) : null}

            {phase === 4 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-2">
                <div className="text-sm font-semibold text-white">Phase 4 — Study plan</div>
                <div className="text-sm text-slate-300">
                  {chat?.complete ? 'Complete. Redirecting…' : 'Generating your study plan…'}
                </div>
              </div>
            ) : null}
          </div>
        </main>
      </div>
    </StudyPlanShell>
  );
}
