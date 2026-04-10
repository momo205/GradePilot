'use client';

import React, { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";

export default function LeftSidebar() {
  return (
    <aside className="h-full w-[300px] bg-[#141B3A]/60 backdrop-blur-xl border border-white/5 p-6 flex flex-col rounded-[24px] shadow-[0_10px_40px_rgba(0,0,0,0.4)] relative">
      {/* Brand Header */}
      <div className="flex items-center gap-4 mb-8 pl-1">
        <div className="w-[42px] h-[42px] flex-shrink-0 rounded-2xl bg-gradient-to-br from-[#62bbf0] to-[#59e3d3] flex items-center justify-center shadow-[0_4px_16px_rgba(98,187,240,0.3)]">
          <svg className="w-[22px] h-[22px] text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <h1 className="text-white font-extrabold text-xl tracking-wide leading-tight mt-0.5">GradePilot</h1>
          <p className="text-[#36d3b7] text-[10px] tracking-wide font-bold mt-1">Autonomous Agent</p>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex flex-col gap-1 mb-5">
        <NavLink href="/dashboard" label="Study Plan" icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
        } />
        <NavLink href="/dashboard/notes" label="Notes" icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
        } />
        <NavLink href="/dashboard/practice" label="Practice" icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
        } />
        <NavLink href="/dashboard/calendar" label="Calendar" icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
        } />
      </nav>

      {/* Sync Google Calendar Button */}
      <button 
        disabled
        title="Coming soon"
        className="flex items-center justify-between w-full py-4 px-5 rounded-[1.25rem] bg-[#23283c] border border-white/[0.03] mb-7 shadow-sm opacity-50 cursor-not-allowed"
      >
        <div className="flex items-center gap-3.5">
          <svg className="w-[18px] h-[18px] text-[#36d3b7]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-white font-extrabold text-[13px] tracking-wide">Sync Google Calendar</span>
        </div>
        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

{/* Agent Command Footer Input */}
      <div className="pt-4 flex flex-col gap-3.5 pl-1">
        <h2 className="text-white text-[13px] font-bold tracking-wide flex items-center gap-2.5">
          <svg className="w-4 h-4 text-[#7364d9]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          Agent Command
        </h2>
        <div className="relative group">
          <input
            type="text"
            placeholder="Ask me anything..."
            className="w-full bg-[#121524] border border-white/5 rounded-2xl py-3.5 px-4 pr-12 text-sm font-medium text-white placeholder:text-slate-400 focus:outline-none focus:border-[#7364d9]/50 focus:ring-1 focus:ring-[#7364d9]/50 transition-all shadow-inner"
          />
          <button className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-slate-500 hover:text-[#7364d9] transition-colors">
            <svg className="w-[18px] h-[18px] -rotate-45 ml-1 mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>

      {/* User Menu */}
      <UserMenu />
    </aside>
  );
}

function NavLink({ href, label, icon }: { href: string; label: string; icon: React.ReactNode }) {
  const pathname = usePathname();
  const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(href));
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-semibold transition-all ${
        active
          ? 'bg-[#00F5D4]/10 text-[#00F5D4] border border-[#00F5D4]/20'
          : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
      }`}
    >
      {icon}
      {label}
    </Link>
  );
}

function UserMenu() {
  const router = useRouter();
  const supabase = createClient();
  const [user, setUser] = useState<User | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
    router.push('/');
    router.refresh();
  };

  const initials = user?.user_metadata?.full_name
    ? user.user_metadata.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0].toUpperCase() ?? '?';

  return (
    <div ref={ref} className="relative mt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-3 w-full p-3 rounded-2xl hover:bg-white/5 transition-colors border border-white/5"
      >
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-[#0B0F2A] shrink-0"
          style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
        >
          {initials}
        </div>
        <div className="flex-1 text-left min-w-0">
          <p className="text-white text-[13px] font-semibold truncate">
            {user?.user_metadata?.full_name ?? 'My Account'}
          </p>
          <p className="text-slate-400 text-[11px] truncate">{user?.email}</p>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform shrink-0 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-[#1a1f3a] border border-white/10 rounded-2xl shadow-xl overflow-hidden z-50">
          <div className="px-4 py-3 border-b border-white/5">
            <p className="text-white text-[13px] font-semibold truncate">
              {user?.user_metadata?.full_name ?? 'My Account'}
            </p>
            <p className="text-slate-400 text-[11px] truncate">{user?.email}</p>
          </div>
          <button
            onClick={signOut}
            className="flex items-center gap-3 w-full px-4 py-3 text-[13px] text-[#FF4D6D] hover:bg-[#FF4D6D]/10 transition-colors font-semibold"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
