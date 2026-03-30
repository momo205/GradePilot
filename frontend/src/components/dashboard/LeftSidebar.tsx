'use client';

import React, { useEffect, useRef, useState } from "react";
import UploadHub from "./UploadHub";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
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

      {/* Sync Google Calendar Button */}
      <button className="flex items-center justify-between w-full py-4 px-5 rounded-[1.25rem] bg-[#23283c] hover:bg-[#2b3047] border border-white/[0.03] transition-colors mb-7 shadow-sm group">
        <div className="flex items-center gap-3.5">
          <svg className="w-[18px] h-[18px] text-[#36d3b7]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-white font-extrabold text-[13px] tracking-wide">Sync Google Calendar</span>
        </div>
        <svg className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors group-hover:rotate-180 duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

      {/* Main Upload Dropzone area */}
      <div className="flex-1 min-h-0 flex flex-col">
        <UploadHub />
      </div>

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
