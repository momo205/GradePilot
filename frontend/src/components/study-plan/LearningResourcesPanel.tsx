'use client';

import React, { useCallback, useState } from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import {
  fetchLearningResources,
  type LearningResourceItemOut,
  type LearningResourcesOut,
} from '@/lib/backend';

function resourceHref(item: LearningResourceItemOut): string {
  const q = encodeURIComponent(item.search_query);
  if (item.destination === 'youtube') {
    return `https://www.youtube.com/results?search_query=${q}`;
  }
  return `https://www.google.com/search?q=${q}`;
}

export function LearningResourcesPanel({
  classId,
  classTitle,
  hasNotes,
  onOpenNotesTab,
}: {
  classId: string;
  classTitle: string;
  hasNotes: boolean;
  onOpenNotesTab: () => void;
}) {
  const [result, setResult] = useState<LearningResourcesOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLocalError(null);
    setLoading(true);
    try {
      const out = await fetchLearningResources(classId);
      setResult(out);
    } catch (e: unknown) {
      setResult(null);
      setLocalError(e instanceof Error ? e.message : 'Could not load suggestions');
    } finally {
      setLoading(false);
    }
  }, [classId]);

  if (!hasNotes) {
    return (
      <EmptyState
        title="Learning resources"
        body={`Add saved notes for “${classTitle}” first. Suggestions are generated from your class title and lecture notes so they stay relevant.`}
        action={
          <button
            type="button"
            onClick={onOpenNotesTab}
            className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold"
          >
            Open Notes
          </button>
        }
      />
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
      <div>
        <div className="text-sm font-semibold text-white">Learning resources</div>
        <p className="mt-1 text-sm text-slate-300 max-w-3xl">
          YouTube and web picks tailored to <span className="text-white font-medium">{classTitle}</span>{' '}
          from your saved notes. Each link runs a search so you can choose a video or article—nothing is
          invented behind the scenes.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={loading}
          onClick={() => void load()}
          className="rounded-xl bg-white text-black px-4 py-2 text-xs font-semibold disabled:opacity-50"
        >
          {loading ? 'Loading…' : result ? 'Refresh suggestions' : 'Get suggestions'}
        </button>
        {result ? (
          <span className="text-[11px] text-slate-500">Model: {result.model}</span>
        ) : null}
      </div>

      {localError ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
          {localError}
        </div>
      ) : null}

      {result && result.items.length > 0 ? (
        <ul className="space-y-3">
          {result.items.map((item, i) => (
            <li
              key={`${item.title}-${i}`}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-white">{item.title}</div>
                  <span className="mt-1 inline-block text-[10px] uppercase tracking-wide text-slate-500">
                    {item.destination === 'youtube' ? 'YouTube search' : 'Web search'}
                  </span>
                </div>
                <a
                  href={resourceHref(item)}
                  target="_blank"
                  rel="noreferrer"
                  className="shrink-0 rounded-lg border border-white/20 bg-white/[0.08] px-2.5 py-1 text-xs font-semibold text-white hover:bg-white/[0.12]"
                >
                  Open search
                </a>
              </div>
              <p className="mt-2 text-sm text-slate-300">{item.rationale}</p>
              <p className="mt-1 text-[11px] text-slate-500 truncate" title={item.search_query}>
                Query: {item.search_query}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
