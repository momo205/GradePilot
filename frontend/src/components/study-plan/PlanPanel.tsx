import React from 'react';
import { EmptyState } from '@/components/study-plan/EmptyState';
import type { StudyPlanOut } from '@/lib/backend';

export function PlanPanel({
  hasNotes,
  plan,
  onGenerate,
  onToggleTask,
  loading,
}: {
  hasNotes: boolean;
  plan: StudyPlanOut | null;
  onGenerate: () => void;
  onToggleTask: (taskText: string, completed: boolean) => void;
  loading: boolean;
}) {
  const completedTasks = plan?.plan_json.completed_tasks ?? [];
  const allTasks = plan?.plan_json.schedule?.flatMap(d => d.tasks) ?? [];
  const totalCount = allTasks.length;
  const completedCount = allTasks.filter(t => completedTasks.includes(t)).length;
  const progressPercent = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);

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
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            {totalCount > 0 ? (
              <div className="flex items-center gap-3 w-full sm:w-1/2">
                <div className="h-2 flex-1 rounded-full bg-white/10 overflow-hidden">
                  <div 
                    className="h-full bg-indigo-500 transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-indigo-400">{progressPercent}%</span>
              </div>
            ) : <div />}
            <button
              disabled={loading}
              onClick={onGenerate}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60 shrink-0"
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
                      <ul className="mt-2 text-sm text-slate-300 space-y-2">
                        {day.tasks.map((t) => {
                          const isCompleted = completedTasks.includes(t);
                          return (
                            <li key={t} className="flex items-start gap-2">
                              <input 
                                type="checkbox"
                                checked={isCompleted}
                                onChange={(e) => onToggleTask(t, e.target.checked)}
                                className="mt-1 w-3.5 h-3.5 rounded border-white/20 bg-white/5 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-0 cursor-pointer shrink-0"
                              />
                              <span className={`transition-colors ${isCompleted ? 'text-indigo-400/60 line-through' : 'text-slate-300'}`}>
                                {t}
                              </span>
                            </li>
                          );
                        })}
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

