import React from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import type { StudyPlanOut } from '@/lib/backend';

export function PlanPanel({
  hasNotes,
  plan,
  onGenerate,
  loading,
}: {
  hasNotes: boolean;
  plan: StudyPlanOut | null;
  onGenerate: () => void;
  loading: boolean;
}) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Study plan</h2>
        <p className="text-sm text-slate-300">Generate a plan from your latest notes.</p>
      </div>

      {!hasNotes ? (
        <EmptyState
          title="No notes yet"
          body="Save notes for this class to generate a study plan."
        />
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
          <div className="flex items-center justify-end">
            <button
              disabled={loading}
              onClick={onGenerate}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              Generate plan
            </button>
          </div>

          {plan ? (
            <div className="space-y-4">
              <div>
                <div className="text-sm font-semibold text-white">
                  {plan.plan_json.title}
                </div>
                {plan.plan_json.goals?.length ? (
                  <ul className="mt-2 text-sm text-slate-300 space-y-1">
                    {plan.plan_json.goals.slice(0, 6).map((g) => (
                      <li key={g}>- {g}</li>
                    ))}
                  </ul>
                ) : null}
              </div>

              {plan.plan_json.schedule?.length ? (
                <div className="space-y-3">
                  {plan.plan_json.schedule.map((day) => (
                    <div
                      key={day.day}
                      className="rounded-xl border border-white/10 bg-black/20 p-3"
                    >
                      <div className="text-sm font-medium text-white">{day.day}</div>
                      <ul className="mt-2 text-sm text-slate-300 space-y-1">
                        {day.tasks.map((t) => (
                          <li key={t}>- {t}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

