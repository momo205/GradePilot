import React from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import type { PracticeQuestion } from '@/lib/backend';

export function PracticePanel({
  hasNotes,
  practiceTopic,
  practiceCount,
  practiceDifficulty,
  onPracticeTopicChange,
  onPracticeCountChange,
  onPracticeDifficultyChange,
  onGenerate,
  loading,
  questions,
}: {
  hasNotes: boolean;
  practiceTopic: string;
  practiceCount: number;
  practiceDifficulty: 'Easy' | 'Medium' | 'Hard';
  onPracticeTopicChange: (v: string) => void;
  onPracticeCountChange: (v: number) => void;
  onPracticeDifficultyChange: (v: 'Easy' | 'Medium' | 'Hard') => void;
  onGenerate: () => void;
  loading: boolean;
  questions: PracticeQuestion[] | null;
}) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Practice questions</h2>
        <p className="text-sm text-slate-300">Generate practice questions for a topic.</p>
      </div>

      {!hasNotes ? (
        <EmptyState
          title="Add notes first"
          body="Practice questions work best when your class has notes saved."
        />
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input
              value={practiceTopic}
              onChange={(e) => onPracticeTopicChange(e.target.value)}
              placeholder="Topic (e.g. Big-O, pointers, recursion)"
              className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
            />
            <input
              type="number"
              min={1}
              max={10}
              value={practiceCount}
              onChange={(e) => onPracticeCountChange(Number(e.target.value))}
              className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
            />
            <select
              value={practiceDifficulty}
              onChange={(e) =>
                onPracticeDifficultyChange(e.target.value as 'Easy' | 'Medium' | 'Hard')
              }
              className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
            >
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </div>

          <div className="flex justify-end">
            <button
              disabled={loading || practiceTopic.trim().length === 0}
              onClick={onGenerate}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              Generate
            </button>
          </div>

          {questions && questions.length > 0 ? (
            <div className="space-y-3">
              {questions.map((q, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-white/10 bg-black/20 p-3"
                >
                  <div className="text-sm font-medium text-white">{q.q}</div>
                  <div className="mt-2 text-sm text-slate-300 whitespace-pre-wrap">
                    {q.a}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

