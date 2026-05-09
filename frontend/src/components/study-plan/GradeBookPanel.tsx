'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import { updateClassGradeBook, type GradeBookState } from '@/lib/backend';
import {
  coursePercentEarned,
  letterForPercent,
  maxPossibleCoursePercent,
  remainingWeightPercent,
  requiredAverageOnRemaining,
  weightsSum,
  type GradeBookComponent,
} from '@/lib/gradeBookMath';

const DEFAULT_CUTOFFS = [
  { letter: 'A', min_percent: 90 },
  { letter: 'B', min_percent: 80 },
  { letter: 'C', min_percent: 70 },
  { letter: 'D', min_percent: 60 },
];

function normalizeBook(raw: GradeBookState | null | undefined): GradeBookState {
  if (!raw) {
    return {
      components: [],
      pass_percent: 60,
      target_percent: 73,
      letter_cutoffs: DEFAULT_CUTOFFS,
    };
  }
  return {
    ...raw,
    letter_cutoffs:
      raw.letter_cutoffs && raw.letter_cutoffs.length > 0
        ? raw.letter_cutoffs
        : DEFAULT_CUTOFFS,
  };
}

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `g${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

export function GradeBookPanel({
  classId,
  gradeBook,
  hasIndexedSyllabus,
  onOpenNotesTab,
  onSaved,
}: {
  classId: string;
  gradeBook: GradeBookState | null | undefined;
  hasIndexedSyllabus: boolean;
  onOpenNotesTab: () => void;
  onSaved: (next: GradeBookState) => void;
}) {
  const [draft, setDraft] = useState<GradeBookState>(() => normalizeBook(gradeBook));
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  // Show the editor once a syllabus is indexed, or anytime a grade book was saved for this class.
  const showWorkspace = hasIndexedSyllabus || gradeBook != null;

  useEffect(() => {
    setDraft(normalizeBook(gradeBook));
  }, [classId, gradeBook]);

  const components = draft.components;

  const earned = useMemo(() => coursePercentEarned(components), [components]);
  const remW = useMemo(() => remainingWeightPercent(components), [components]);
  const bestCase = useMemo(() => maxPossibleCoursePercent(components), [components]);
  const letterNow = useMemo(
    () => letterForPercent(earned, draft.letter_cutoffs),
    [earned, draft.letter_cutoffs]
  );
  const letterBest = useMemo(
    () => letterForPercent(bestCase, draft.letter_cutoffs),
    [bestCase, draft.letter_cutoffs]
  );

  const avgToPass = useMemo(
    () => requiredAverageOnRemaining(components, draft.pass_percent),
    [components, draft.pass_percent]
  );
  const avgToTarget = useMemo(
    () => requiredAverageOnRemaining(components, draft.target_percent),
    [components, draft.target_percent]
  );

  const weightTotal = useMemo(() => weightsSum(components), [components]);
  const weightsOk = components.length === 0 || Math.abs(weightTotal - 100) < 0.02;

  const passGuidance = useMemo(() => {
    if (components.length === 0) {
      return 'Add one row per graded category from your syllabus (weights must total 100%).';
    }
    if (!weightsOk) {
      return `Weights currently sum to ${weightTotal.toFixed(1)}% — adjust so they total 100% before saving.`;
    }
    if (remW < 1e-6) {
      if (earned >= draft.pass_percent) {
        return `All categories graded. Your course average is ${earned.toFixed(1)}%, at or above your pass line (${draft.pass_percent}%).`;
      }
      return `All categories graded at ${earned.toFixed(1)}%, below your pass line (${draft.pass_percent}%).`;
    }
    if (earned >= draft.pass_percent) {
      return `You are already at or above the pass line (${draft.pass_percent}%) even counting ungraded work as 0%.`;
    }
    if (avgToPass == null) return null;
    if (avgToPass > 100) {
      return `Passing (${draft.pass_percent}%) may not be reachable on the remaining ${remW.toFixed(0)}% of the grade — check weights or talk to your instructor.`;
    }
    if (avgToPass <= 0) {
      return `You can stay below 0% on remaining work and still pass (you are already there).`;
    }
    return `To reach ${draft.pass_percent}% overall, you need about ${avgToPass.toFixed(1)}% average on the remaining ${remW.toFixed(0)}% of the grade.`;
  }, [components.length, weightsOk, weightTotal, remW, earned, draft.pass_percent, avgToPass]);

  const targetGuidance = useMemo(() => {
    if (components.length === 0 || !weightsOk) return null;
    if (remW < 1e-6) {
      if (earned >= draft.target_percent) {
        return `You have reached your goal (${draft.target_percent}%) with ${earned.toFixed(1)}%.`;
      }
      return `Graded work so far: ${earned.toFixed(1)}%, below your goal (${draft.target_percent}%).`;
    }
    if (avgToTarget == null) return null;
    if (avgToTarget > 100) {
      return `Your goal (${draft.target_percent}%) may need extra credit — you would need over 100% on the remaining ${remW.toFixed(0)}%.`;
    }
    if (avgToTarget <= 0) {
      return `You can miss everything left and still meet ${draft.target_percent}% — you are well ahead.`;
    }
    return `To reach ${draft.target_percent}% overall, aim for about ${avgToTarget.toFixed(1)}% average on the remaining ${remW.toFixed(0)}%.`;
  }, [components.length, weightsOk, remW, earned, draft.target_percent, avgToTarget]);

  const updateComponent = useCallback((id: string, patch: Partial<GradeBookComponent>) => {
    setDraft((d) => ({
      ...d,
      components: d.components.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
  }, []);

  const addRow = useCallback(() => {
    setDraft((d) => ({
      ...d,
      components: [
        ...d.components,
        {
          id: newId(),
          name: 'Category (match your syllabus)',
          weight_percent: 0,
          score_percent: null,
        },
      ],
    }));
  }, []);

  const removeRow = useCallback((id: string) => {
    setDraft((d) => ({
      ...d,
      components: d.components.filter((c) => c.id !== id),
    }));
  }, []);

  async function save() {
    setLocalError(null);
    if (draft.components.length > 0 && !weightsOk) {
      setLocalError('Weights must sum to 100% (within 0.02).');
      return;
    }
    setSaving(true);
    try {
      const saved = await updateClassGradeBook(classId, draft);
      onSaved(saved);
    } catch (e: unknown) {
      setLocalError(e instanceof Error ? e.message : 'Could not save grade book');
    } finally {
      setSaving(false);
    }
  }

  const bands = useMemo(() => {
    const cut = [...draft.letter_cutoffs].sort((a, b) => a.min_percent - b.min_percent);
    const segments: { letter: string; from: number; to: number }[] = [];
    for (let i = 0; i < cut.length; i++) {
      const from = cut[i]!.min_percent;
      const to = i + 1 < cut.length ? cut[i + 1]!.min_percent : 100;
      segments.push({ letter: cut[i]!.letter, from, to });
    }
    if (cut.length > 0 && cut[0]!.min_percent > 0) {
      segments.unshift({ letter: 'F', from: 0, to: cut[0]!.min_percent });
    }
    return segments;
  }, [draft.letter_cutoffs]);

  if (!showWorkspace) {
    return (
      <EmptyState
        title="Grade outlook"
        body="This uses the grading breakdown from your course syllabus. Index your syllabus first in Notes & Q&A (upload or paste text and set document type to Syllabus). Then enter each graded category and its weight exactly as your instructor lists them—every course is different, so we don’t use a preset template."
        action={
          <button
            type="button"
            onClick={onOpenNotesTab}
            className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold"
          >
            Open Notes &amp; Q&amp;A
          </button>
        }
      />
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
      <div>
        <div className="text-sm font-semibold text-white">Grade outlook</div>
        <p className="mt-1 text-sm text-slate-300 max-w-3xl">
          Enter categories and weights from your indexed syllabus.
          Weights must total 100%. Add your score on each item when graded; leave blank until then.
          Letter bands below should match the syllabus—adjust cutoffs if your course uses different ranges.
        </p>
      </div>

      {localError ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
          {localError}
        </div>
      ) : null}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Pass line (course %)</label>
          <input
            type="number"
            min={0}
            max={100}
            step={0.5}
            value={draft.pass_percent}
            onChange={(e) =>
              setDraft((d) => ({ ...d, pass_percent: Number(e.target.value) }))
            }
            className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm text-white"
          />
          <p className="mt-1 text-[11px] text-slate-500">Often 60% for a D; set from your syllabus.</p>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Your goal (course %)</label>
          <input
            type="number"
            min={0}
            max={100}
            step={0.5}
            value={draft.target_percent}
            onChange={(e) =>
              setDraft((d) => ({ ...d, target_percent: Number(e.target.value) }))
            }
            className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm text-white"
          />
          <p className="mt-1 text-[11px] text-slate-500">e.g. 73 for a low C, 80 for a B.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={addRow}
          className="rounded-xl border border-white/20 bg-white/[0.06] px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/[0.1]"
        >
          + Add category from syllabus
        </button>
      </div>

      {components.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-3 py-2 font-semibold">Category</th>
                <th className="px-3 py-2 font-semibold w-24">Weight %</th>
                <th className="px-3 py-2 font-semibold w-28">Your %</th>
                <th className="px-3 py-2 w-10" />
              </tr>
            </thead>
            <tbody>
              {components.map((c) => (
                <tr key={c.id} className="border-b border-white/5">
                  <td className="px-3 py-2">
                    <input
                      value={c.name}
                      onChange={(e) => updateComponent(c.id, { name: e.target.value })}
                      className="w-full min-w-[140px] bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-sm text-white"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={c.weight_percent}
                      onChange={(e) =>
                        updateComponent(c.id, { weight_percent: Number(e.target.value) })
                      }
                      className="w-full bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-sm text-white"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      placeholder="—"
                      value={c.score_percent ?? ''}
                      onChange={(e) => {
                        const v = e.target.value.trim();
                        updateComponent(c.id, {
                          score_percent: v === '' ? null : Number(v),
                        });
                      }}
                      className="w-full bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-sm text-white placeholder:text-slate-600"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => removeRow(c.id)}
                      className="text-xs text-slate-400 hover:text-rose-300"
                      aria-label="Remove row"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className={weightsOk ? 'text-slate-400' : 'text-amber-200'}>
          Weights sum: <strong className="text-white">{weightTotal.toFixed(1)}%</strong>
          {components.length > 0 ? (weightsOk ? ' · OK' : ' · must be 100%') : ''}
        </span>
        <button
          type="button"
          disabled={saving || (components.length > 0 && !weightsOk)}
          onClick={() => void save()}
          className="rounded-xl bg-white text-black px-4 py-2 text-xs font-semibold disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save grade setup'}
        </button>
      </div>

      {components.length > 0 && weightsOk ? (
        <>
          <div className="rounded-xl border border-white/10 bg-black/20 p-3 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Your standing
            </div>
            <ul className="text-sm text-slate-300 space-y-1 list-disc list-inside">
              <li>
                <span className="text-white font-medium">{earned.toFixed(1)}%</span> toward the
                course total so far (ungraded categories count as 0%). Letter pace:{' '}
                <span className="text-white font-medium">{letterNow}</span>.
              </li>
              <li>
                Best case if you earn 100% on everything left:{' '}
                <span className="text-white font-medium">{bestCase.toFixed(1)}%</span> (
                {letterBest}).
              </li>
            </ul>
            <p className="text-sm text-slate-300">{passGuidance}</p>
            {targetGuidance ? (
              <p className="text-sm text-slate-300 border-t border-white/10 pt-2">{targetGuidance}</p>
            ) : null}
          </div>

          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
              Grade scale (edit cutoffs to match syllabus)
            </div>
            <div className="flex h-9 w-full overflow-hidden rounded-lg border border-white/10">
              {bands.map((seg) => {
                const w = Math.max(0, seg.to - seg.from);
                const hue =
                  seg.letter === 'A'
                    ? '142 70% 36%'
                    : seg.letter === 'B'
                      ? '142 45% 32%'
                      : seg.letter === 'C'
                        ? '45 90% 42%'
                        : seg.letter === 'D'
                          ? '25 90% 45%'
                          : '0 70% 40%';
                return (
                  <div
                    key={`${seg.letter}-${seg.from}`}
                    title={`${seg.letter}: ${seg.from}–${seg.to}%`}
                    className="flex items-center justify-center text-[10px] font-bold text-white/90"
                    style={{
                      width: `${w}%`,
                      backgroundColor: `hsl(${hue})`,
                    }}
                  >
                    {seg.letter}
                  </div>
                );
              })}
            </div>
            <div className="relative mt-3 h-2 rounded bg-white/10">
              <div
                className="absolute top-1/2 h-0 w-0 -translate-x-1/2 -translate-y-1/2 border-x-8 border-x-transparent border-b-8 border-b-white"
                style={{ left: `${Math.min(100, Math.max(0, earned))}%` }}
                title={`You (so far): ${earned.toFixed(1)}%`}
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Triangle marks your current earned % (missing work as 0). Bands are approximate —
              always confirm letter rules on the syllabus.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {draft.letter_cutoffs.map((row, i) => (
              <div key={row.letter} className="flex items-center gap-1">
                <input
                  value={row.letter}
                  onChange={(e) => {
                    const v = e.target.value;
                    setDraft((d) => {
                      const letter_cutoffs = d.letter_cutoffs.map((c, j) =>
                        j === i ? { ...c, letter: v } : c
                      );
                      return { ...d, letter_cutoffs };
                    });
                  }}
                  className="w-10 bg-black/30 border border-white/10 rounded px-1 py-0.5 text-xs text-white text-center"
                />
                <span className="text-xs text-slate-500">≥</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={row.min_percent}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setDraft((d) => {
                      const letter_cutoffs = d.letter_cutoffs.map((c, j) =>
                        j === i ? { ...c, min_percent: v } : c
                      );
                      return { ...d, letter_cutoffs };
                    });
                  }}
                  className="w-14 bg-black/30 border border-white/10 rounded px-1 py-0.5 text-xs text-white"
                />
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
