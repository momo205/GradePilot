'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  addNotes,
  askClass,
  createDeadline,
  createStudyPlan,
  deleteDeadline,
  extractPdfText,
  generatePractice,
  getClassNotes,
  getClassSummary,
  getLatestStudyPlan,
  getGoogleCalendarInfo,
  getUserSettings,
  listDeadlines,
  runReplanner,
  syncClassToGoogleCalendar,
  summariseDocument,
  updateClassTimeline,
  updateDeadline,
  updateUserSettings,
  uploadMaterialPdf,
  uploadMaterialText,
  type ClassAskOut,
  type ClassSummaryOut,
  type DeadlineOut,
  type MaterialIngestOut,
  type MeetingPattern,
  type NotesOut,
  type PracticeQuestion,
  type ScheduledSession,
  type StudyPlanOut,
  type SummariseOut,
} from '@/lib/backend';
import { createClient } from '@/lib/supabase/client';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';
import { NotesPanel } from '@/components/study-plan/NotesPanel';
import { PracticePanel } from '@/components/study-plan/PracticePanel';
import { RagPanel } from '@/components/study-plan/RagPanel';
import { PlanPanel } from '@/components/study-plan/PlanPanel';

type Tab = 'overview' | 'deadlines' | 'notes' | 'practice';

async function filesToText(files: File[]): Promise<{ filename: string; text: string }> {
  const parts: string[] = [];
  for (const f of files) {
    const lower = f.name.toLowerCase();
    if (lower.endsWith('.txt') || lower.endsWith('.md')) {
      parts.push(await f.text());
      continue;
    }
    if (lower.endsWith('.pdf')) {
      const { raw_text } = await extractPdfText(f);
      parts.push(raw_text);
      continue;
    }
    throw new Error('Only .txt, .md, and .pdf uploads are supported. Please upload a supported file type.');
  }
  return { filename: files.map((f) => f.name).join(', '), text: parts.join('\n\n') };
}

export default function ClassDashboardClient({ classId }: { classId: string }) {
  const supabase = createClient();

  const [tab, setTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [summary, setSummary] = useState<ClassSummaryOut | null>(null);

  const [notes, setNotes] = useState<NotesOut[] | null>(null);
  const [notesDraft, setNotesDraft] = useState('');
  const [notesSummary, setNotesSummary] = useState<SummariseOut | null>(null);
  const [summarising, setSummarising] = useState(false);
  const [lastUpload, setLastUpload] = useState<{ filename: string; text: string } | null>(null);

  const [deadlines, setDeadlines] = useState<DeadlineOut[] | null>(null);
  const [deadlineTitle, setDeadlineTitle] = useState('');
  const [deadlineDue, setDeadlineDue] = useState('');

  const [practiceTopic, setPracticeTopic] = useState('');
  const [practiceCount, setPracticeCount] = useState(5);
  const [practiceDifficulty, setPracticeDifficulty] = useState<'Easy' | 'Medium' | 'Hard'>(
    'Medium'
  );
  const [practice, setPractice] = useState<PracticeQuestion[] | null>(null);

  const [plan, setPlan] = useState<StudyPlanOut | null>(null);

  const [ragIngestResult, setRagIngestResult] = useState<MaterialIngestOut | null>(null);
  const [ragAskResult, setRagAskResult] = useState<ClassAskOut | null>(null);
  const [ragQuestion, setRagQuestion] = useState('');
  const [ragUploadDocType, setRagUploadDocType] = useState('reading');
  const [ragAskDocFilter, setRagAskDocFilter] = useState('');
  const [ragPasteToIndex, setRagPasteToIndex] = useState('');
  const [googleConnected, setGoogleConnected] = useState<boolean | null>(null);
  const [googleSyncBusy, setGoogleSyncBusy] = useState(false);
  const [calendarSyncHint, setCalendarSyncHint] = useState<string | null>(null);
  const [calendarId, setCalendarId] = useState<string | null>(null);

  const [autoSchedule, setAutoSchedule] = useState<boolean>(false);
  const [savingAutoSchedule, setSavingAutoSchedule] = useState<boolean>(false);

  const [meetingPatternDraft, setMeetingPatternDraft] =
    useState<MeetingPattern>({
      weekdays: [],
      start_time: '14:00',
      end_time: '15:30',
    });
  const [savingMeetingPattern, setSavingMeetingPattern] = useState(false);
  const [meetingPatternHint, setMeetingPatternHint] = useState<string | null>(
    null
  );

  const [lastScheduledSession, setLastScheduledSession] =
    useState<ScheduledSession | null>(null);
  const [autoSchedulingBusy, setAutoSchedulingBusy] = useState(false);
  const [autoSchedulingHint, setAutoSchedulingHint] = useState<string | null>(
    null
  );

  const classTitle = summary?.clazz?.title ?? 'Class';

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const s = await getClassSummary(classId);
        if (cancelled) return;
        setSummary(s);
        const [n, d, settings] = await Promise.all([
          getClassNotes(classId),
          listDeadlines(classId),
          getUserSettings(),
        ]);
        if (cancelled) return;
        setNotes(n);
        setDeadlines(d);
        setGoogleConnected(settings.googleConnected);
        setAutoSchedule(Boolean(settings.autoScheduleSessions));
        if (s.clazz.meeting_pattern) {
          setMeetingPatternDraft({
            weekdays: s.clazz.meeting_pattern.weekdays ?? [],
            start_time: s.clazz.meeting_pattern.start_time ?? '14:00',
            end_time: s.clazz.meeting_pattern.end_time ?? '15:30',
          });
        }
        if (settings.googleConnected) {
          try {
            const info = await getGoogleCalendarInfo();
            if (!cancelled) setCalendarId(info.calendar_id);
          } catch {
            // Calendar embed is optional; ignore failures.
            if (!cancelled) setCalendarId(null);
          }
        } else {
          setCalendarId(null);
        }
        if (s.latest_study_plan_id) {
          const latest = await getLatestStudyPlan(classId);
          if (!cancelled) setPlan(latest);
        } else {
          setPlan(null);
        }
      } catch (e: unknown) {
        if (!cancelled && !controller.signal.aborted)
          setError(e instanceof Error ? e.message : 'Failed to load class');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [classId]);

  async function persistAutoSchedule(next: boolean): Promise<void> {
    setSavingAutoSchedule(true);
    try {
      const updated = await updateUserSettings({ autoScheduleSessions: next });
      setAutoSchedule(Boolean(updated.autoScheduleSessions));
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : 'Failed to save auto-schedule setting'
      );
    } finally {
      setSavingAutoSchedule(false);
    }
  }

  function explainSchedulingErrors(errors: string[]): string | null {
    for (const e of errors) {
      if (e.includes('skip:no_google_integration'))
        return 'Connect Google Calendar from the Classes page to enable scheduling.';
      if (e.includes('skip:insufficient_scopes'))
        return 'Reconnect Google Calendar — required calendar permissions are missing.';
      if (e.includes('skip:no_notes'))
        return 'Add or upload notes for this class first.';
      if (e.includes('skip:anchor_in_past'))
        return 'No upcoming lecture or deadline to anchor against. Add a deadline or set a meeting pattern.';
      if (e.includes('skip:no_slot_found'))
        return 'No free 60-minute slot found before the next lecture/deadline. Try widening your preferred study windows.';
      if (e.includes('schedule_study_session_'))
        return 'Could not schedule a session. Try again, or check Google Calendar access.';
    }
    return null;
  }

  async function triggerScheduling(opts: { manual: boolean }): Promise<void> {
    setAutoSchedulingBusy(true);
    setAutoSchedulingHint(null);
    try {
      const result = await runReplanner(classId, {
        trigger: opts.manual ? 'manual_replan' : 'notes_added',
        force_schedule_session: opts.manual,
      });
      setLastScheduledSession(result.scheduled_session);
      if (result.scheduled_session) {
        setAutoSchedulingHint(null);
        return;
      }
      const friendly = explainSchedulingErrors(result.errors ?? []);
      if (friendly) {
        setAutoSchedulingHint(friendly);
      } else if (opts.manual) {
        setAutoSchedulingHint(
          'No session was scheduled. Check meeting pattern, deadlines, and preferred study windows.'
        );
      } else if (autoSchedule && googleConnected !== true) {
        setAutoSchedulingHint(
          'Auto-schedule is on but Google Calendar is not connected yet.'
        );
      }
    } catch (e: unknown) {
      setAutoSchedulingHint(
        e instanceof Error ? e.message : 'Could not run smart scheduling.'
      );
    } finally {
      setAutoSchedulingBusy(false);
    }
  }

  const upcomingDeadlines = useMemo(() => {
    const all = deadlines ?? [];
    return all
      .filter((d) => !d.completed_at)
      .slice()
      .sort((a, b) => {
        const da = a.due_at ? Date.parse(a.due_at) : Number.POSITIVE_INFINITY;
        const db = b.due_at ? Date.parse(b.due_at) : Number.POSITIVE_INFINITY;
        return da - db;
      })
      .slice(0, 3);
  }, [deadlines]);

  return (
    <StudyPlanShell
      title={classTitle}
      subtitle="Overview, deadlines, notes, practice, and course Q&A."
      actions={
        <div className="flex items-center gap-4">
          <Link href="/classes" className="text-sm text-slate-300 hover:text-white transition-colors">
            Back to Classes
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

      <div className="flex flex-wrap gap-2 mb-6">
        {(['overview', 'deadlines', 'notes', 'practice'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={[
              'px-3 py-1.5 rounded-xl text-sm font-semibold border transition-colors',
              tab === t
                ? 'border-white/20 bg-white/10 text-white'
                : 'border-white/10 bg-white/[0.03] text-slate-300 hover:text-white hover:bg-white/[0.06]',
            ].join(' ')}
          >
            {t[0]!.toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="text-sm font-semibold text-white">Next deadlines</div>
              <div className="mt-3 space-y-2">
                {upcomingDeadlines.length === 0 ? (
                  <div className="text-sm text-slate-300">No upcoming deadlines.</div>
                ) : (
                  upcomingDeadlines.map((d) => (
                    <div key={d.id} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                      <div className="text-sm text-white">{d.title}</div>
                      <div className="text-xs text-slate-300">
                        {d.due_at ? new Date(d.due_at).toLocaleString() : d.due_text}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="text-sm font-semibold text-white">Latest study plan</div>
              <div className="mt-3">
                {plan ? (
                  <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                    <div className="text-sm font-semibold text-white">{plan.plan_json.title}</div>
                    <div className="mt-2 text-sm text-slate-300">
                      {plan.plan_json.goals?.slice(0, 3).map((g) => (
                        <div key={g}>- {g}</div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-slate-300">
                    No plan yet. Generate one from notes in the Notes tab.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">
                  Lecture meeting pattern
                </div>
                <p className="mt-1 text-sm text-slate-300 max-w-xl">
                  Tell GradePilot when this class meets. Smart scheduling will
                  use the next lecture as the deadline for your study session.
                </p>
              </div>
              {meetingPatternHint ? (
                <span className="text-xs text-emerald-400">
                  {meetingPatternHint}
                </span>
              ) : null}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const).map(
                (label, idx) => {
                  const active = meetingPatternDraft.weekdays.includes(idx);
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => {
                        setMeetingPatternDraft((p) => ({
                          ...p,
                          weekdays: active
                            ? p.weekdays.filter((d) => d !== idx)
                            : [...p.weekdays, idx].sort(),
                        }));
                      }}
                      className={[
                        'rounded-lg px-2.5 py-1 text-xs font-semibold border',
                        active
                          ? 'border-white/30 bg-white text-black'
                          : 'border-white/15 bg-black/20 text-slate-200 hover:bg-white/[0.06]',
                      ].join(' ')}
                    >
                      {label}
                    </button>
                  );
                }
              )}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-300">
              <span>From</span>
              <input
                value={meetingPatternDraft.start_time}
                onChange={(e) =>
                  setMeetingPatternDraft((p) => ({
                    ...p,
                    start_time: e.target.value,
                  }))
                }
                placeholder="14:00"
                className="w-20 bg-black/40 border border-white/10 rounded-lg px-2 py-1 text-sm text-white"
              />
              <span>to</span>
              <input
                value={meetingPatternDraft.end_time}
                onChange={(e) =>
                  setMeetingPatternDraft((p) => ({
                    ...p,
                    end_time: e.target.value,
                  }))
                }
                placeholder="15:30"
                className="w-20 bg-black/40 border border-white/10 rounded-lg px-2 py-1 text-sm text-white"
              />
              <button
                type="button"
                disabled={
                  savingMeetingPattern ||
                  meetingPatternDraft.weekdays.length === 0
                }
                onClick={async () => {
                  setSavingMeetingPattern(true);
                  setMeetingPatternHint(null);
                  setError(null);
                  try {
                    await updateClassTimeline(classId, {
                      meeting_pattern: meetingPatternDraft,
                    });
                    setMeetingPatternHint('Saved.');
                  } catch (e: unknown) {
                    setError(
                      e instanceof Error ? e.message : 'Failed to save pattern'
                    );
                  } finally {
                    setSavingMeetingPattern(false);
                  }
                }}
                className="ml-1 rounded-xl bg-white text-black px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
              >
                {savingMeetingPattern ? 'Saving…' : 'Save pattern'}
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">
                  Study session
                </div>
                <p className="mt-1 text-sm text-slate-300 max-w-xl">
                  Books a 60-minute focused-study event on your GradePilot
                  Google calendar before your next lecture or deadline.
                </p>
              </div>
              <button
                type="button"
                disabled={autoSchedulingBusy || googleConnected !== true}
                onClick={() => triggerScheduling({ manual: true })}
                className="rounded-xl border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              >
                {autoSchedulingBusy ? 'Scheduling…' : 'Schedule study session now'}
              </button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
              <label className="inline-flex items-center gap-2 text-sm text-white">
                <input
                  type="checkbox"
                  checked={autoSchedule}
                  disabled={
                    savingAutoSchedule || googleConnected !== true
                  }
                  onChange={(e) => persistAutoSchedule(e.target.checked)}
                />
                Auto-schedule on every notes upload
              </label>
              {googleConnected !== true ? (
                <span className="text-xs text-amber-200/90">
                  Connect Google from{' '}
                  <Link href="/classes" className="underline hover:text-white">
                    Classes
                  </Link>{' '}
                  first.
                </span>
              ) : (
                <Link
                  href="/classes"
                  className="ml-auto text-xs text-slate-300 hover:text-white underline"
                >
                  Edit preferred study windows →
                </Link>
              )}
            </div>

            {lastScheduledSession ? (
              <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-3">
                <div className="text-sm font-semibold text-white">
                  {new Date(lastScheduledSession.start).toLocaleString()} →{' '}
                  {new Date(lastScheduledSession.end).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
                <div className="mt-1 text-xs text-slate-300">
                  Anchor:{' '}
                  {lastScheduledSession.anchor_kind.replace('_', ' ')}
                  {lastScheduledSession.in_preferred_window
                    ? ' · in your preferred window'
                    : ' · outside your preferred windows (best slot available)'}
                </div>
                {lastScheduledSession.calendar_event_link ? (
                  <a
                    href={lastScheduledSession.calendar_event_link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-xs text-slate-200 hover:text-white underline"
                  >
                    Open in Google Calendar
                  </a>
                ) : null}
              </div>
            ) : (
              <div className="mt-3 text-sm text-slate-300">
                No session booked yet. Click <em>Schedule study session now</em>,
                or enable auto-schedule on the Classes page so it runs after
                every notes upload.
              </div>
            )}

            {autoSchedulingHint ? (
              <p className="mt-2 text-xs text-amber-200/90">
                {autoSchedulingHint}
              </p>
            ) : null}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="text-sm font-semibold text-white">Calendar</div>
                <p className="mt-1 text-sm text-slate-300">
                  Your GradePilot deadlines calendar in Google Calendar.
                </p>
              </div>
              {calendarId ? (
                <a
                  className="text-sm text-slate-300 hover:text-white underline"
                  href={`https://calendar.google.com/calendar/u/0/r?cid=${encodeURIComponent(
                    calendarId
                  )}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open in Google Calendar
                </a>
              ) : null}
            </div>

            {googleConnected !== true ? (
              <p className="mt-3 text-sm text-amber-200/90">
                Connect Google Calendar from{' '}
                <Link href="/classes" className="underline hover:text-white">
                  Classes
                </Link>{' '}
                to see your calendar here.
              </p>
            ) : calendarId ? (
              <div className="mt-4 rounded-xl overflow-hidden border border-white/10 bg-black/20">
                <iframe
                  title="GradePilot calendar"
                  className="w-full h-[600px]"
                  src={`https://calendar.google.com/calendar/embed?src=${encodeURIComponent(
                    calendarId
                  )}&ctz=UTC`}
                />
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-300">
                Calendar connected, but embed is not available yet. Try syncing deadlines first.
              </p>
            )}
          </div>
        </div>
      ) : null}

      {tab === 'deadlines' ? (
        <section className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">Google Calendar</div>
                <p className="mt-1 text-xs text-slate-400 max-w-xl">
                  Push this class&apos;s deadlines to your GradePilot calendar (create or update events).
                </p>
              </div>
              <button
                type="button"
                disabled={
                  googleSyncBusy ||
                  googleConnected !== true ||
                  (deadlines ?? []).length === 0
                }
                onClick={async () => {
                  setGoogleSyncBusy(true);
                  setError(null);
                  setCalendarSyncHint(null);
                  try {
                    const { created } = await syncClassToGoogleCalendar(classId);
                    setCalendarSyncHint(
                      created === 0
                        ? 'No deadlines to sync.'
                        : `Updated ${created} deadline event${created === 1 ? '' : 's'} in Google Calendar.`
                    );
                  } catch (err: unknown) {
                    setError(err instanceof Error ? err.message : 'Calendar sync failed');
                  } finally {
                    setGoogleSyncBusy(false);
                  }
                }}
                className="shrink-0 rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {googleSyncBusy ? 'Syncing…' : 'Sync to Google Calendar'}
              </button>
            </div>
            {googleConnected === false ? (
              <p className="text-xs text-amber-200/90">
                Connect Google from{' '}
                <Link href="/classes" className="underline hover:text-white">
                  Classes
                </Link>{' '}
                first.
              </p>
            ) : null}
            {calendarSyncHint ? (
              <p className="text-xs text-emerald-400">{calendarSyncHint}</p>
            ) : null}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
            <div className="text-sm font-semibold text-white">Deadlines</div>
            <div className="space-y-2">
              {(deadlines ?? []).length === 0 ? (
                <div className="text-sm text-slate-300">No deadlines yet.</div>
              ) : (
                (deadlines ?? []).map((d) => (
                  <div
                    key={d.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <input
                        type="checkbox"
                        checked={Boolean(d.completed_at)}
                        onChange={async (e) => {
                          setLoading(true);
                          setError(null);
                          try {
                            const updated = await updateDeadline(classId, d.id, {
                              completed: e.target.checked,
                            });
                            setDeadlines((prev) =>
                              (prev ?? []).map((x) => (x.id === d.id ? updated : x))
                            );
                          } catch (err: unknown) {
                            setError(err instanceof Error ? err.message : 'Failed to update deadline');
                          } finally {
                            setLoading(false);
                          }
                        }}
                        disabled={loading}
                      />
                      <div className="min-w-0">
                        <div className="text-sm text-white truncate">{d.title}</div>
                        <div className="text-xs text-slate-300 truncate">
                          {d.due_at ? new Date(d.due_at).toLocaleString() : d.due_text}
                        </div>
                      </div>
                    </div>
                    <button
                      className="text-xs text-slate-300 hover:text-white"
                      disabled={loading}
                      onClick={async () => {
                        setLoading(true);
                        setError(null);
                        try {
                          await deleteDeadline(classId, d.id);
                          setDeadlines((prev) => (prev ?? []).filter((x) => x.id !== d.id));
                        } catch (err: unknown) {
                          setError(err instanceof Error ? err.message : 'Failed to delete deadline');
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <input
                value={deadlineTitle}
                onChange={(e) => setDeadlineTitle(e.target.value)}
                placeholder="Deadline title"
                className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
              />
              <input
                value={deadlineDue}
                onChange={(e) => setDeadlineDue(e.target.value)}
                placeholder="Due (YYYY-MM-DD)"
                className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
              />
              <button
                disabled={loading || deadlineTitle.trim().length === 0 || deadlineDue.trim().length === 0}
                onClick={async () => {
                  setLoading(true);
                  setError(null);
                  try {
                    const created = await createDeadline(classId, deadlineTitle.trim(), deadlineDue.trim());
                    setDeadlines((prev) => [created, ...(prev ?? [])]);
                    setDeadlineTitle('');
                    setDeadlineDue('');
                  } catch (err: unknown) {
                    setError(err instanceof Error ? err.message : 'Failed to add deadline');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
              >
                Add deadline
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {tab === 'notes' ? (
        <div className="space-y-10">
          <NotesPanel
            classTitle={classTitle}
            notes={notes}
            notesDraft={notesDraft}
            onNotesDraftChange={setNotesDraft}
            loading={loading}
            summarising={summarising}
            notesSummary={notesSummary}
            onUploadFiles={async (files) => {
              setError(null);
              setLoading(true);
              setNotesSummary(null);
              try {
                const { filename, text } = await filesToText(files);
                setLastUpload({ filename, text });
                const created = await addNotes(classId, text.trim());
                setNotes((prev) => [created, ...(prev ?? [])]);
                setNotesDraft('');
                void triggerScheduling({ manual: false });
              } catch (err: unknown) {
                setError(err instanceof Error ? err.message : 'Failed to upload notes');
              } finally {
                setLoading(false);
              }
            }}
            onSummariseNotes={async () => {
              setError(null);
              setSummarising(true);
              setNotesSummary(null);
              try {
                const filename = lastUpload?.filename ?? 'Notes';
                const text = (notesDraft.trim() || lastUpload?.text || '').trim();
                if (!text) throw new Error('Add or upload notes before summarising.');
                const result = await summariseDocument(filename, text);
                setNotesSummary(result);
              } catch (err: unknown) {
                setError(err instanceof Error ? err.message : 'Failed to summarise notes');
              } finally {
                setSummarising(false);
              }
            }}
            onSaveNotes={async () => {
              setLoading(true);
              setError(null);
              try {
                const created = await addNotes(classId, notesDraft.trim());
                setNotes((prev) => [created, ...(prev ?? [])]);
                setNotesDraft('');
                setNotesSummary(null);
                setLastUpload(null);
                void triggerScheduling({ manual: false });
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : 'Failed to save notes');
              } finally {
                setLoading(false);
              }
            }}
          />

          <RagPanel
            loading={loading}
            ingestResult={ragIngestResult}
            askResult={ragAskResult}
            question={ragQuestion}
            onQuestionChange={setRagQuestion}
            uploadDocType={ragUploadDocType}
            onUploadDocTypeChange={setRagUploadDocType}
            askDocTypeFilter={ragAskDocFilter}
            onAskDocTypeFilterChange={setRagAskDocFilter}
            pasteToIndex={ragPasteToIndex}
            onPasteToIndexChange={setRagPasteToIndex}
            onUploadPdf={async (file) => {
              setLoading(true);
              setError(null);
              setRagAskResult(null);
              try {
                const out = await uploadMaterialPdf(classId, file, ragUploadDocType);
                setRagIngestResult(out);
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : 'Failed to index PDF');
              } finally {
                setLoading(false);
              }
            }}
            onIndexPastedText={async () => {
              const text = ragPasteToIndex.trim();
              if (!text) return;
              setLoading(true);
              setError(null);
              setRagAskResult(null);
              try {
                const out = await uploadMaterialText(classId, text, 'pasted-notes.txt', ragUploadDocType);
                setRagIngestResult(out);
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : 'Failed to index text');
              } finally {
                setLoading(false);
              }
            }}
            onAsk={async () => {
              const q = ragQuestion.trim();
              if (!q) return;
              setLoading(true);
              setError(null);
              try {
                const out = await askClass(classId, q, {
                  top_k: 6,
                  document_type: ragAskDocFilter || null,
                });
                setRagAskResult(out);
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : 'Failed to get answer');
              } finally {
                setLoading(false);
              }
            }}
          />

          <PlanPanel
            hasNotes={Boolean(notes && notes.length > 0)}
            plan={plan}
            loading={loading}
            onGenerate={async () => {
              setLoading(true);
              setError(null);
              try {
                const latestNotesId = notes?.[0]?.id;
                const created = await createStudyPlan(classId, latestNotesId);
                setPlan(created);
                if (autoSchedule) {
                  void triggerScheduling({ manual: false });
                }
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : 'Failed to generate plan');
              } finally {
                setLoading(false);
              }
            }}
          />
        </div>
      ) : null}

      {tab === 'practice' ? (
        <PracticePanel
          hasNotes={Boolean(notes && notes.length > 0)}
          practiceTopic={practiceTopic}
          practiceCount={practiceCount}
          practiceDifficulty={practiceDifficulty}
          onPracticeTopicChange={setPracticeTopic}
          onPracticeCountChange={setPracticeCount}
          onPracticeDifficultyChange={setPracticeDifficulty}
          loading={loading}
          questions={practice}
          onGenerate={async () => {
            setLoading(true);
            setError(null);
            try {
              const res = await generatePractice(classId, practiceTopic.trim(), practiceCount, practiceDifficulty);
              setPractice(res.questions);
            } catch (e: unknown) {
              setError(e instanceof Error ? e.message : 'Failed to generate practice');
            } finally {
              setLoading(false);
            }
          }}
        />
      ) : null}

      {loading && !summary ? <div className="text-sm text-slate-400 mt-4">Loading…</div> : null}
    </StudyPlanShell>
  );
}

