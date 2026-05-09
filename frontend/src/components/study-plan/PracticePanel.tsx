'use client';

import React, { useEffect, useState } from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import type { PracticeQuestion } from '@/lib/backend';

export function PracticePanel({
  hasNotes,
  lectureCount,
  practiceCount,
  practiceDifficulty,
  onPracticeCountChange,
  onPracticeDifficultyChange,
  onGenerate,
  loading,
  questions,
}: {
  hasNotes: boolean;
  lectureCount: number;
  practiceCount: number;
  practiceDifficulty: 'Easy' | 'Medium' | 'Hard';
  onPracticeCountChange: (v: number) => void;
  onPracticeDifficultyChange: (v: 'Easy' | 'Medium' | 'Hard') => void;
  onGenerate: () => void;
  loading: boolean;
  questions: PracticeQuestion[] | null;
}) {
  const [showingAnswer, setShowingAnswer] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    setShowingAnswer(new Set());
  }, [questions]);

  function setFace(index: number, answerFace: boolean) {
    setShowingAnswer((prev) => {
      const next = new Set(prev);
      if (answerFace) next.add(index);
      else next.delete(index);
      return next;
    });
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Practice questions</h2>
        <p className="text-sm text-slate-300">
          Questions are generated from the notes you&apos;ve already saved for this class—no topic
          to pick. Each saved note batch is treated as its own lecture (numbered in the order you
          added them). Each card shows the question first; the answer stays on the back until you
          flip it.
        </p>
        {hasNotes && lectureCount > 0 ? (
          <p className="mt-2 text-xs text-slate-400">
            This class has <span className="text-slate-300 font-medium">{lectureCount}</span>{' '}
            saved lecture{lectureCount === 1 ? '' : 's'} (Lecture 1 = earliest notes, Lecture{' '}
            {lectureCount} = most recent).
          </p>
        ) : null}
      </div>

      {!hasNotes ? (
        <EmptyState
          title="Add notes first"
          body="Save at least one note batch for this class. Practice will pull from that material and label questions by lecture."
        />
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Number of questions</label>
              <input
                type="number"
                min={1}
                max={10}
                value={practiceCount}
                onChange={(e) => {
                  const val = Math.min(10, Math.max(1, Number(e.target.value)));
                  onPracticeCountChange(val);
                }}
                className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Difficulty</label>
              <select
                value={practiceDifficulty}
                onChange={(e) =>
                  onPracticeDifficultyChange(e.target.value as 'Easy' | 'Medium' | 'Hard')
                }
                className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
              >
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              disabled={loading}
              onClick={onGenerate}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              Generate from notes
            </button>
          </div>

          {questions && questions.length > 0 ? (
            <div className="space-y-3">
              {questions.map((q, idx) => {
                const label = q.source_label?.trim() || 'Class notes';
                const back = showingAnswer.has(idx);
                return (
                  <div
                    key={idx}
                    className={[
                      'rounded-xl border p-4 transition-colors',
                      back
                        ? 'border-emerald-500/25 bg-emerald-950/20'
                        : 'border-white/10 bg-black/20',
                    ].join(' ')}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                      <span
                        className={[
                          'inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
                          back
                            ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200/90'
                            : 'border-white/15 bg-white/[0.06] text-slate-200',
                        ].join(' ')}
                      >
                        From {label}
                      </span>
                      <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        {back ? 'Back · Answer' : 'Front · Question'}
                      </span>
                    </div>

                    {back ? (
                      <>
                        <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                          {q.a}
                        </p>
                        <button
                          type="button"
                          onClick={() => setFace(idx, false)}
                          className="mt-4 w-full rounded-xl border border-white/20 bg-white/[0.06] py-2.5 text-sm font-semibold text-white hover:bg-white/[0.1] transition-colors"
                        >
                          Flip to question
                        </button>
                      </>
                    ) : (
                      <>
                        <p className="text-sm font-medium text-white leading-relaxed">{q.q}</p>
                        <button
                          type="button"
                          onClick={() => setFace(idx, true)}
                          className="mt-4 w-full rounded-xl border border-white/20 bg-white/[0.06] py-2.5 text-sm font-semibold text-white hover:bg-white/[0.1] transition-colors"
                        >
                          Flip to answer
                        </button>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
