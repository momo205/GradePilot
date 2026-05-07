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
  onToggleDeadline,
  allowAdd,
}: {
  deadlines: { id: string; title: string; due_text: string; completed_at?: string | null }[];
  deadlineTitle: string;
  deadlineDue: string;
  onDeadlineTitleChange: (v: string) => void;
  onDeadlineDueChange: (v: string) => void;
  onAddDeadline: () => void;
  onRemoveDeadline: (id: string) => void;
  onToggleDeadline: (id: string, completed: boolean) => void;
  allowAdd: boolean;
}) {
  const completedCount = deadlines.filter((d) => d.completed_at).length;
  const totalCount = deadlines.length;
  const progressPercent = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Deadlines</h2>
        <p className="text-sm text-slate-300">
          Add deadlines from a syllabus upload or enter them manually.
        </p>
      </div>

      {totalCount > 0 && (
        <div className="flex items-center gap-3">
          <div className="h-2 flex-1 rounded-full bg-white/10 overflow-hidden">
            <div 
              className="h-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="text-xs font-medium text-emerald-400">{progressPercent}%</span>
        </div>
      )}

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
              className={`flex items-center justify-between rounded-xl border border-white/10 px-3 py-2 transition-colors ${d.completed_at ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-black/20'}`}
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <input 
                  type="checkbox"
                  checked={!!d.completed_at}
                  onChange={(e) => onToggleDeadline(d.id, e.target.checked)}
                  className="w-4 h-4 rounded border-white/20 bg-white/5 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0 cursor-pointer"
                />
                <div className="min-w-0">
                  <div className={`text-sm truncate transition-colors ${d.completed_at ? 'text-emerald-400/80 line-through' : 'text-white'}`}>{d.title}</div>
                  <div className={`text-xs truncate transition-colors ${d.completed_at ? 'text-emerald-500/50' : 'text-slate-300'}`}>{d.due_text}</div>
                </div>
              </div>
              <button
                className="text-xs text-slate-300 hover:text-white shrink-0 ml-4"
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

