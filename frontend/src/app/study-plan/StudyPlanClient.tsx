'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  addNotes,
  askClass,
  createClass,
  createDeadline,
  createStudyPlan,
  deleteDeadline,
  extractPdfText,
  generatePractice,
  getClassNotes,
  listClasses,
  listDeadlines,
  summariseDocument,
  uploadMaterialPdf,
  uploadMaterialText,
  type ClassAskOut,
  type ClassOut,
  type DeadlineOut,
  type MaterialIngestOut,
  type NotesOut,
  type PracticeQuestion,
  type StudyPlanOut,
  type SummariseOut,
} from '@/lib/backend';
import { createClient } from '@/lib/supabase/client';
import { StudyPlanShell } from '@/components/study-plan/StudyPlanShell';
import { EmptyState } from '@/components/study-plan/EmptyState';
import { ClassesPanel } from '@/components/study-plan/ClassesPanel';
import { NotesPanel } from '@/components/study-plan/NotesPanel';
import { DeadlinesPanel } from '@/components/study-plan/DeadlinesPanel';
import { PracticePanel } from '@/components/study-plan/PracticePanel';
import { PlanPanel } from '@/components/study-plan/PlanPanel';
import { RagPanel } from '@/components/study-plan/RagPanel';

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

export default function StudyPlanClient() {
  const supabase = createClient();
  const [classes, setClasses] = useState<ClassOut[] | null>(null);
  const [selectedClassId, setSelectedClassId] = useState<string | null>(null);
  const selectedClass = useMemo(
    () => classes?.find((c) => c.id === selectedClassId) ?? null,
    [classes, selectedClassId]
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newClassTitle, setNewClassTitle] = useState('');

  const [notes, setNotes] = useState<NotesOut[] | null>(null);
  const [notesDraft, setNotesDraft] = useState('');
  const [notesSummary, setNotesSummary] = useState<SummariseOut | null>(null);
  const [summarising, setSummarising] = useState(false);
  const [lastUpload, setLastUpload] = useState<{ filename: string; text: string } | null>(null);

  const [practiceTopic, setPracticeTopic] = useState('');
  const [practiceCount, setPracticeCount] = useState(5);
  const [practiceDifficulty, setPracticeDifficulty] = useState<'Easy' | 'Medium' | 'Hard'>(
    'Medium'
  );
  const [practice, setPractice] = useState<PracticeQuestion[] | null>(null);

  const [plan, setPlan] = useState<StudyPlanOut | null>(null);

  const [deadlines, setDeadlines] = useState<DeadlineOut[] | null>(null);
  const [deadlineTitle, setDeadlineTitle] = useState('');
  const [deadlineDue, setDeadlineDue] = useState('');

  const [ragIngestResult, setRagIngestResult] = useState<MaterialIngestOut | null>(null);
  const [ragAskResult, setRagAskResult] = useState<ClassAskOut | null>(null);
  const [ragQuestion, setRagQuestion] = useState('');
  const [ragUploadDocType, setRagUploadDocType] = useState('syllabus');
  const [ragAskDocFilter, setRagAskDocFilter] = useState('');
  const [ragPasteToIndex, setRagPasteToIndex] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        const res = await listClasses();
        if (cancelled) return;
        setClasses(res);
        setSelectedClassId(res[0]?.id ?? null);
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

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedClassId) {
        setNotes(null);
        setPlan(null);
        setPractice(null);
        setNotesDraft('');
        setNotesSummary(null);
        setRagIngestResult(null);
        setRagAskResult(null);
        setRagQuestion('');
        setRagPasteToIndex('');
        return;
      }
      try {
        setError(null);
        const res = await getClassNotes(selectedClassId);
        if (cancelled) return;
        setNotes(res);
        const d = await listDeadlines(selectedClassId);
        if (cancelled) return;
        setDeadlines(d);
        setPlan(null);
        setPractice(null);
        setNotesDraft('');
        setNotesSummary(null);
        setRagIngestResult(null);
        setRagAskResult(null);
        setRagQuestion('');
        setRagPasteToIndex('');
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load notes');
        setNotes([]);
        setDeadlines([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedClassId]);

  return (
    <StudyPlanShell
      title="Study Plan"
      subtitle="A focused workspace for classes, notes, Q&A on indexed materials, deadlines, and practice."
      actions={
        <button
          onClick={async () => {
            await supabase.auth.signOut();
            window.location.href = '/';
          }}
          className="text-sm text-slate-300 hover:text-white transition-colors"
        >
          Sign out
        </button>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        <ClassesPanel
          classes={classes}
          selectedClassId={selectedClassId}
          newClassTitle={newClassTitle}
          onNewClassTitleChange={setNewClassTitle}
          creating={loading}
          onCreateClass={async () => {
            setLoading(true);
            setError(null);
            try {
              const created = await createClass(newClassTitle.trim());
              setClasses((prev) => [created, ...(prev ?? [])]);
              setSelectedClassId(created.id);
              setNewClassTitle('');
            } catch (e: unknown) {
              setError(e instanceof Error ? e.message : 'Failed to create class');
            } finally {
              setLoading(false);
            }
          }}
          onSelectClass={setSelectedClassId}
        />

        <main className="lg:col-span-8 space-y-10">
          {error ? (
            <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          {!selectedClass ? (
            <EmptyState
              title="Pick a class"
              body="Select a class (or add one) to start uploading notes and generating a plan."
            />
          ) : (
            <>
              <NotesPanel
                classTitle={selectedClass.title}
                notes={notes}
                notesDraft={notesDraft}
                onNotesDraftChange={setNotesDraft}
                loading={loading}
                summarising={summarising}
                notesSummary={notesSummary}
                onUploadFiles={async (files) => {
                  if (!selectedClassId) return;
                  setError(null);
                  setLoading(true);
                  setNotesSummary(null);
                  try {
                    const { filename, text } = await filesToText(files);
                    setLastUpload({ filename, text });
                    const created = await addNotes(selectedClassId, text.trim());
                    setNotes((prev) => [created, ...(prev ?? [])]);
                    setNotesDraft('');
                    setPlan(null);
                    setPractice(null);
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
                    if (!text) {
                      throw new Error('Add or upload notes before summarising.');
                    }
                    const result = await summariseDocument(filename, text);
                    setNotesSummary(result);
                  } catch (err: unknown) {
                    setError(err instanceof Error ? err.message : 'Failed to summarise notes');
                  } finally {
                    setSummarising(false);
                  }
                }}
                onImportDateAsDeadline={async (dueText) => {
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  try {
                    const created = await createDeadline(
                      selectedClassId,
                      'Imported date',
                      dueText
                    );
                    setDeadlines((prev) => [created, ...(prev ?? [])]);
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to add deadline');
                  } finally {
                    setLoading(false);
                  }
                }}
                onSaveNotes={async () => {
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  try {
                    const created = await addNotes(selectedClassId, notesDraft.trim());
                    setNotes((prev) => [created, ...(prev ?? [])]);
                    setNotesDraft('');
                    setNotesSummary(null);
                    setLastUpload(null);
                    setPlan(null);
                    setPractice(null);
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
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  setRagAskResult(null);
                  try {
                    const out = await uploadMaterialPdf(
                      selectedClassId,
                      file,
                      ragUploadDocType
                    );
                    setRagIngestResult(out);
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to index PDF');
                  } finally {
                    setLoading(false);
                  }
                }}
                onIndexPastedText={async () => {
                  if (!selectedClassId) return;
                  const text = ragPasteToIndex.trim();
                  if (!text) return;
                  setLoading(true);
                  setError(null);
                  setRagAskResult(null);
                  try {
                    const out = await uploadMaterialText(
                      selectedClassId,
                      text,
                      'pasted-notes.txt',
                      ragUploadDocType
                    );
                    setRagIngestResult(out);
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to index text');
                  } finally {
                    setLoading(false);
                  }
                }}
                onAsk={async () => {
                  if (!selectedClassId) return;
                  const q = ragQuestion.trim();
                  if (!q) return;
                  setLoading(true);
                  setError(null);
                  try {
                    const out = await askClass(selectedClassId, q, {
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

              <DeadlinesPanel
                deadlines={(deadlines ?? []).map((d) => ({
                  id: d.id,
                  title: d.title,
                  due_text: d.due_text,
                }))}
                deadlineTitle={deadlineTitle}
                deadlineDue={deadlineDue}
                onDeadlineTitleChange={setDeadlineTitle}
                onDeadlineDueChange={setDeadlineDue}
                allowAdd={Boolean(selectedClassId)}
                onAddDeadline={async () => {
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  try {
                    const created = await createDeadline(
                      selectedClassId,
                      deadlineTitle.trim(),
                      deadlineDue.trim()
                    );
                    setDeadlines((prev) => [created, ...(prev ?? [])]);
                    setDeadlineTitle('');
                    setDeadlineDue('');
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to add deadline');
                  } finally {
                    setLoading(false);
                  }
                }}
                onRemoveDeadline={async (id) => {
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  try {
                    await deleteDeadline(selectedClassId, id);
                    setDeadlines((prev) => (prev ?? []).filter((d) => d.id !== id));
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to remove deadline');
                  } finally {
                    setLoading(false);
                  }
                }}
              />

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
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  try {
                    const res = await generatePractice(
                      selectedClassId,
                      practiceTopic.trim(),
                      practiceCount,
                      practiceDifficulty
                    );
                    setPractice(res.questions);
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to generate practice');
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
                  if (!selectedClassId) return;
                  setLoading(true);
                  setError(null);
                  try {
                    const latestNotesId = notes?.[0]?.id;
                    const created = await createStudyPlan(selectedClassId, latestNotesId);
                    setPlan(created);
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : 'Failed to generate plan');
                  } finally {
                    setLoading(false);
                  }
                }}
              />
            </>
          )}
        </main>
      </div>
    </StudyPlanShell>
  );
}

