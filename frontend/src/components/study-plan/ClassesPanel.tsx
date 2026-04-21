import React from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import type { ClassOut } from '@/lib/backend';

export function ClassesPanel({
  classes,
  selectedClassId,
  newClassTitle,
  onNewClassTitleChange,
  onCreateClass,
  onSelectClass,
  creating,
}: {
  classes: ClassOut[] | null;
  selectedClassId: string | null;
  newClassTitle: string;
  onNewClassTitleChange: (v: string) => void;
  onCreateClass: () => void;
  onSelectClass: (id: string) => void;
  creating: boolean;
}) {
  return (
    <aside className="lg:col-span-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Classes</h2>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <label className="block">
          <span className="text-xs font-medium text-slate-300">Add a class</span>
          <div className="mt-2 flex gap-2">
            <input
              value={newClassTitle}
              onChange={(e) => onNewClassTitleChange(e.target.value)}
              placeholder='e.g. "CS 101 — Data Structures"'
              className="flex-1 bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
            />
            <button
              disabled={creating || newClassTitle.trim().length === 0}
              onClick={onCreateClass}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              Add
            </button>
          </div>
        </label>
      </div>

      <div className="mt-4 space-y-2">
        {classes === null ? (
          <div className="text-sm text-slate-300">Loading…</div>
        ) : classes.length === 0 ? (
          <EmptyState
            title="No classes yet"
            body="Add your first class to start building a plan."
          />
        ) : (
          classes.map((c) => (
            <button
              key={c.id}
              onClick={() => onSelectClass(c.id)}
              className={`w-full text-left rounded-2xl border px-4 py-3 transition-colors ${
                selectedClassId === c.id
                  ? 'border-white/20 bg-white/10'
                  : 'border-white/10 bg-white/[0.03] hover:bg-white/[0.06]'
              }`}
            >
              <div className="text-sm font-medium text-white">{c.title}</div>
              <div className="mt-1 text-xs text-slate-300">
                Created {new Date(c.created_at).toLocaleDateString()}
              </div>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}

