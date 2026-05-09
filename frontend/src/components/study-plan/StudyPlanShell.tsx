import Link from 'next/link';
import React from 'react';

export function StudyPlanShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full bg-[#0A0B10] text-[#F8FAFC]">
      <div className="sticky top-0 z-50 border-b border-white/10 bg-[#0A0B10]/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-6 h-14 flex items-center justify-between gap-4">
          <Link
            href="/"
            className="text-sm font-medium tracking-tight text-white hover:text-slate-200 transition-colors shrink-0"
          >
            GradePilot
          </Link>
          {actions ? (
            <div className="flex flex-wrap items-center justify-end gap-3 sm:gap-4 min-w-0">
              {actions}
            </div>
          ) : null}
        </div>
      </div>

      <header className="px-6 py-5 border-b border-white/10">
        <div className="mx-auto max-w-6xl">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
            {subtitle ? (
              <p className="mt-1 text-sm text-slate-300">{subtitle}</p>
            ) : null}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 py-10">{children}</div>
    </div>
  );
}

