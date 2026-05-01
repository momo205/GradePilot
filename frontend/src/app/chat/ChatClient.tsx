'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  createOrGetChatSession,
  getChatSession,
  importDeadlinesFromSyllabus,
  sendChatMessage,
  uploadMaterialPdf,
  uploadMaterialText,
  type ChatReplyOut,
  type ChatToolAction,
} from '@/lib/backend';
import { createClient } from '@/lib/supabase/client';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';

type ToolCard = { title: string; detail?: string };

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatReplyOut | null>(null);
  const [toolCards, setToolCards] = useState<ToolCard[]>([]);

  const rawPhase = chat?.state?.phase;
  const phase =
    typeof rawPhase === 'number'
      ? rawPhase
      : typeof rawPhase === 'string'
        ? Number(rawPhase) || 1
        : 1;
  const classId = useMemo(() => {
    const direct = chat?.class_id;
    if (typeof direct === 'string' && direct) return direct;
    const fromState = chat?.state?.class_id;
    if (typeof fromState === 'string' && fromState) return fromState;
    return null;
  }, [chat]);

  const [classTitle, setClassTitle] = useState('');
  const [timezone, setTimezone] = useState('America/New_York');
  const [semesterStart, setSemesterStart] = useState('');
  const [semesterEnd, setSemesterEnd] = useState('');

  const [deadlineTitle, setDeadlineTitle] = useState('');
  const [deadlineDue, setDeadlineDue] = useState('');

  const [materialDocType, setMaterialDocType] = useState<'reading' | 'notes' | 'assignment'>(
    'reading'
  );
  const [pasteToIndex, setPasteToIndex] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const sess = await createOrGetChatSession();
        if (cancelled) return;
        setSessionId(sess.id);
        const reply = await getChatSession(sess.id);
        if (cancelled) return;
        setChat(reply);
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
  }, []);

  useEffect(() => {
    if (chat?.complete && chat.class_id) {
      router.push(`/classes/${chat.class_id}`);
    }
  }, [chat?.complete, chat?.class_id, router]);

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
              Phase: <span className="text-white">{phase}</span> / 5
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

            {/* Phase controls */}
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
                <div className="text-sm font-semibold text-white">Phase 2 — Semester timeline</div>
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
                    Save timeline
                  </button>
                </div>
              </div>
            ) : null}

            {phase === 3 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-4">
                <div className="text-sm font-semibold text-white">Phase 3 — Deadlines</div>
                <div className="text-xs text-slate-400">
                  Upload a syllabus PDF to extract deadlines, or add deadlines manually below.
                </div>

                <label className="text-sm text-slate-300 hover:text-white cursor-pointer rounded-xl border border-white/15 bg-white/[0.03] px-4 py-2 inline-block">
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    disabled={loading || !classId}
                    onChange={async (e) => {
                      const f = e.target.files?.[0];
                      e.target.value = '';
                      if (!f || !classId) return;
                      setLoading(true);
                      setError(null);
                      try {
                        await uploadMaterialPdf(classId, f, 'syllabus');
                        const imported = await importDeadlinesFromSyllabus(classId, f);
                        setToolCards((prev) => [
                          { title: 'Imported deadlines', detail: `${imported.created} created` },
                          ...prev,
                        ]);
                        await sendRaw(JSON.stringify({ deadlines_imported: true }));
                      } catch (err: unknown) {
                        setError(err instanceof Error ? err.message : 'Upload/import failed');
                      } finally {
                        setLoading(false);
                      }
                    }}
                  />
                  Upload syllabus PDF
                </label>

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
                    disabled={loading || !deadlineTitle.trim() || !deadlineDue.trim()}
                    onClick={() => {
                      void sendRaw(
                        JSON.stringify({
                          deadline: { title: deadlineTitle.trim(), due: deadlineDue.trim() },
                        })
                      );
                      setDeadlineTitle('');
                      setDeadlineDue('');
                    }}
                    className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
                  >
                    Add deadline
                  </button>
                </div>

                <div className="flex justify-end">
                  <button
                    disabled={loading}
                    onClick={() => void sendRaw('done')}
                    className="rounded-xl border border-white/15 bg-white/[0.03] text-slate-100 px-4 py-2 text-sm font-semibold hover:bg-white/[0.06] disabled:opacity-60"
                  >
                    Done with deadlines
                  </button>
                </div>
              </div>
            ) : null}

            {phase === 4 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-4">
                <div className="text-sm font-semibold text-white">Phase 4 — Materials</div>
                <div className="text-xs text-slate-400">
                  Upload readings/slides/notes for Q&amp;A (optional). When finished, click Done.
                </div>

                <div className="flex flex-wrap items-end gap-3">
                  <div className="grid gap-1">
                    <label className="text-xs text-slate-400">Document type</label>
                    <select
                      value={materialDocType}
                      onChange={(e) =>
                        setMaterialDocType(e.target.value as typeof materialDocType)
                      }
                      className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm min-w-[160px]"
                    >
                      <option value="reading">reading</option>
                      <option value="notes">notes</option>
                      <option value="assignment">assignment</option>
                    </select>
                  </div>

                  <label className="text-sm text-slate-300 hover:text-white cursor-pointer rounded-xl border border-white/15 bg-white/[0.03] px-4 py-2">
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      className="hidden"
                      disabled={loading || !classId}
                      onChange={async (e) => {
                        const f = e.target.files?.[0];
                        e.target.value = '';
                        if (!f || !classId) return;
                        setLoading(true);
                        setError(null);
                        try {
                          const out = await uploadMaterialPdf(classId, f, materialDocType);
                          setToolCards((prev) => [
                            { title: 'Indexed material', detail: `${out.chunks_created} chunks` },
                            ...prev,
                          ]);
                        } catch (err: unknown) {
                          setError(err instanceof Error ? err.message : 'Upload failed');
                        } finally {
                          setLoading(false);
                        }
                      }}
                    />
                    Upload PDF
                  </label>
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-slate-400">Or paste text to index</label>
                  <textarea
                    value={pasteToIndex}
                    onChange={(e) => setPasteToIndex(e.target.value)}
                    placeholder="Paste text here to index…"
                    className="w-full min-h-[100px] bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                  <div className="flex justify-end">
                    <button
                      disabled={loading || !classId || pasteToIndex.trim().length === 0}
                      onClick={async () => {
                        if (!classId) return;
                        setLoading(true);
                        setError(null);
                        try {
                          const out = await uploadMaterialText(
                            classId,
                            pasteToIndex.trim(),
                            'pasted.txt',
                            materialDocType
                          );
                          setPasteToIndex('');
                          setToolCards((prev) => [
                            { title: 'Indexed pasted text', detail: `${out.chunks_created} chunks` },
                            ...prev,
                          ]);
                        } catch (err: unknown) {
                          setError(err instanceof Error ? err.message : 'Index failed');
                        } finally {
                          setLoading(false);
                        }
                      }}
                      className="rounded-xl border border-white/15 bg-white/[0.03] text-slate-100 px-4 py-2 text-sm font-semibold hover:bg-white/[0.06] disabled:opacity-60"
                    >
                      Index text
                    </button>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    disabled={loading}
                    onClick={() => void sendRaw('done')}
                    className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
                  >
                    Done → Generate plan
                  </button>
                </div>
              </div>
            ) : null}

            {phase === 5 ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-2">
                <div className="text-sm font-semibold text-white">Phase 5 — Study plan</div>
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

