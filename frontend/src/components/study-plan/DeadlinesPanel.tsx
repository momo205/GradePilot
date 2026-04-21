import React from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';

export function DeadlinesPanel({
  deadlines,
  deadlineTitle,
  deadlineDue,
  onDeadlineTitleChange,
  onDeadlineDueChange,
  onAddDeadline,
  onRemoveDeadline,
  allowAdd,
}: {
  deadlines: { id: string; title: string; due_text: string }[];
  deadlineTitle: string;
  deadlineDue: string;
  onDeadlineTitleChange: (v: string) => void;
  onDeadlineDueChange: (v: string) => void;
  onAddDeadline: () => void;
  onRemoveDeadline: (id: string) => void;
  allowAdd: boolean;
}) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Deadlines</h2>
        <p className="text-sm text-slate-300">
          Add deadlines from a syllabus upload or enter them manually.
        </p>
      </div>

      {deadlines.length === 0 ? (
        <EmptyState
          title="No deadlines yet"
          body="Add a deadline manually (or import dates found in your uploads)."
        />
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-2">
          {deadlines.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 px-3 py-2"
            >
              <div className="min-w-0">
                <div className="text-sm text-white truncate">{d.title}</div>
                <div className="text-xs text-slate-300 truncate">{d.due_text}</div>
              </div>
              <button
                className="text-xs text-slate-300 hover:text-white"
                onClick={() => onRemoveDeadline(d.id)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input
            value={deadlineTitle}
            onChange={(e) => onDeadlineTitleChange(e.target.value)}
            placeholder="Deadline title"
            className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
          />
          <input
            value={deadlineDue}
            onChange={(e) => onDeadlineDueChange(e.target.value)}
            placeholder="Due date (YYYY-MM-DD)"
            className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
          />
          <button
            disabled={!allowAdd || deadlineTitle.trim().length === 0 || deadlineDue.trim().length === 0}
            onClick={onAddDeadline}
            className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
          >
            Add deadline
          </button>
        </div>
      </div>
    </section>
  );
}

