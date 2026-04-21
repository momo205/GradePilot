import React from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import type { NotesOut, SummariseOut } from '@/lib/backend';

export function NotesPanel({
  classTitle,
  notes,
  notesDraft,
  onNotesDraftChange,
  onUploadFiles,
  onSummariseNotes,
  onSaveNotes,
  onImportDateAsDeadline,
  loading,
  summarising,
  notesSummary,
}: {
  classTitle: string;
  notes: NotesOut[] | null;
  notesDraft: string;
  onNotesDraftChange: (v: string) => void;
  onUploadFiles: (files: File[]) => void;
  onSummariseNotes: () => void;
  onSaveNotes: () => void;
  onImportDateAsDeadline?: (dueText: string) => void;
  loading: boolean;
  summarising: boolean;
  notesSummary: SummariseOut | null;
}) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Notes</h2>
        <p className="text-sm text-slate-300">Add notes for “{classTitle}”.</p>
      </div>

      {notes && notes.length > 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-xs font-medium text-slate-300 mb-3">
            {notes.length} note{notes.length === 1 ? '' : 's'}
          </div>
          <div className="space-y-3">
            {notes.slice(0, 5).map((n) => (
              <div
                key={n.id}
                className="rounded-xl border border-white/10 bg-black/20 p-3"
              >
                <div className="text-xs text-slate-300">
                  {new Date(n.created_at).toLocaleString()}
                </div>
                <div className="mt-2 text-sm text-slate-200 whitespace-pre-wrap line-clamp-5">
                  {n.notes_text}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          title="No notes yet"
          body="Upload or paste notes to unlock practice questions and a study plan."
        />
      )}

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">Add notes</p>
          <label className="text-xs text-slate-300 hover:text-white cursor-pointer">
            <input
              type="file"
              className="hidden"
              multiple
              accept=".txt,.md,.pdf"
              onChange={(e) => {
                const files = Array.from(e.target.files ?? []);
                e.target.value = '';
                if (files.length === 0) return;
                onUploadFiles(files);
              }}
            />
            Upload .txt/.md/.pdf
          </label>
        </div>

        {summarising ? <div className="text-sm text-slate-300">Summarising…</div> : null}

        <textarea
          value={notesDraft}
          onChange={(e) => onNotesDraftChange(e.target.value)}
          placeholder="Paste notes here (or upload a file)."
          className="w-full min-h-[160px] bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-white/20"
        />

        {notesSummary?.important_dates?.length ? (
          <div className="rounded-xl border border-white/10 bg-black/20 p-3">
            <p className="text-xs font-medium text-slate-200">
              Dates found in upload
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-300">
              {notesSummary.important_dates.slice(0, 6).map((d) => (
                <li key={d} className="flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate">- {d}</span>
                  {onImportDateAsDeadline ? (
                    <button
                      type="button"
                      onClick={() => onImportDateAsDeadline(d)}
                      className="shrink-0 text-xs text-slate-300 hover:text-white"
                    >
                      Add as deadline
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex items-center justify-end gap-2">
          <button
            disabled={loading || summarising || notesDraft.trim().length === 0}
            onClick={onSummariseNotes}
            className="rounded-xl border border-white/15 bg-white/[0.03] text-slate-100 px-4 py-2 text-sm font-semibold hover:bg-white/[0.06] disabled:opacity-60"
          >
            Summarize notes
          </button>
          <button
            disabled={loading || notesDraft.trim().length === 0}
            onClick={onSaveNotes}
            className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
          >
            Save notes
          </button>
        </div>
      </div>
    </section>
  );
}

