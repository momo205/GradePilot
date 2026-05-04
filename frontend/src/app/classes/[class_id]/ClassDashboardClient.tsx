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
  listDeadlines,
  summariseDocument,
  updateDeadline,
  uploadMaterialPdf,
  uploadMaterialText,
  type ClassAskOut,
  type ClassSummaryOut,
  type DeadlineOut,
  type MaterialIngestOut,
  type NotesOut,
  type PracticeQuestion,
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
    throw new Error('Only .txt, .md, and .pdf uploads are supported right now.');
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

  const classTitle = summary?.clazz?.title ?? 'Class';

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const s = await getClassSummary(classId);
        if (cancelled) return;
        setSummary(s);
        const [n, d] = await Promise.all([getClassNotes(classId), listDeadlines(classId)]);
        if (cancelled) return;
        setNotes(n);
        setDeadlines(d);
        if (s.latest_study_plan_id) {
          const latest = await getLatestStudyPlan(classId);
          if (!cancelled) setPlan(latest);
        } else {
          setPlan(null);
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load class');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [classId]);

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
        </div>
      ) : null}

      {tab === 'deadlines' ? (
        <section className="space-y-4">
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

