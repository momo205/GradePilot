import React from "react";

export default function RightSidebar() {
  return (
    <aside className="h-full w-[300px] bg-[#161825]/95 border border-white/5 p-6 pb-2 flex flex-col rounded-3xl shadow-xl shadow-black/30 relative">
      {/* Activity Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/5">
        <h2 className="text-white font-extrabold text-[13px] tracking-wide flex items-center gap-2">
          <svg className="w-4 h-4 text-[#36d3b7]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          Live Agent Activity
        </h2>
        <div className="relative flex h-2 w-2 mr-1">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#36d3b7] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[#36d3b7] shadow-[0_0_8px_rgba(54,211,183,0.8)]"></span>
        </div>
      </div>

      {/* Activity Timeline (Issue 20) */}
      <div className="flex-1 pr-2 mt-5 relative overflow-y-auto custom-scrollbar">
        {/* Continuous Timeline Vertical Line */}
        <div className="absolute left-[8px] top-6 bottom-8 w-px bg-white/[0.08]"></div>

        <div className="space-y-7 pb-4">
          {/* Timeline Item 1 */}
          <div className="relative pl-9">
            <div className="absolute left-0 top-1.5 bg-[#161825] border border-white/10 rounded-full text-slate-400 p-1 flex items-center justify-center z-10 shadow-sm">
              <svg className="w-[10px] h-[10px]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
            </div>
            <p className="text-slate-400 text-[9px] font-extrabold tracking-[0.1em] uppercase flex items-center gap-1.5 mt-2">
              10:05 AM
            </p>
            <p className="text-slate-300 text-[11px] mt-1.5 leading-relaxed font-semibold">Extracted 3 deadlines from Biology Syllabus PDF</p>
          </div>
          
          {/* Timeline Item 2 */}
          <div className="relative pl-9">
            <div className="absolute left-0 top-1.5 bg-[#161825] border border-white/10 rounded-full text-slate-400 p-1 flex items-center justify-center z-10 shadow-sm">
              <svg className="w-[10px] h-[10px]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </div>
            <p className="text-slate-400 text-[9px] font-extrabold tracking-[0.1em] uppercase mt-2">
              11:30 AM
            </p>
            <p className="text-slate-300 text-[11px] mt-1.5 leading-relaxed font-semibold">Cross-referenced deadlines with Google Calendar</p>
          </div>
          
          {/* Timeline Item 3 */}
          <div className="relative pl-9">
             <div className="absolute left-0 top-1.5 bg-[#161825] border border-white/10 rounded-full text-slate-400 p-1 flex items-center justify-center z-10 shadow-sm">
              <svg className="w-[10px] h-[10px]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
            </div>
            <p className="text-slate-400 text-[9px] font-extrabold tracking-[0.1em] uppercase mt-2">
              1:15 PM
            </p>
            <p className="text-slate-300 text-[11px] mt-1.5 leading-relaxed font-semibold">Drafted study plan for CS 101 Midterm</p>
          </div>

          {/* Timeline Item 4 (Warning/Reschedule) */}
          <div className="relative pl-9">
            <div className="absolute left-0 top-[-2px] bg-[#161825] border border-rose-500/50 rounded-full text-rose-500 p-1 flex items-center justify-center z-10 shadow-[0_0_8px_rgba(244,63,94,0.3)] bg-rose-500/10">
              <svg className="w-[10px] h-[10px]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <p className="text-rose-500 text-[9px] font-extrabold tracking-[0.1em] uppercase">
              2:00 PM
            </p>
            <p className="text-rose-400/90 text-[11px] mt-1.5 leading-relaxed font-bold border-l-2 border-rose-500/30 pl-3 ml-[-12px]">
              Rearranged CS 101 study schedule because you missed yesterday's session.
            </p>
          </div>

          {/* Timeline Item 5 (Current state) */}
          <div className="relative pl-9">
             <div className="absolute left-0 top-1 bg-[#161825] border border-[#36d3b7] rounded-full text-[#36d3b7] p-1 flex items-center justify-center z-10 shadow-[0_0_10px_rgba(54,211,183,0.4)] bg-[#36d3b7]/10">
              <svg className="w-[10px] h-[10px]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /></svg>
            </div>
            <p className="text-[#36d3b7] text-[10px] font-extrabold tracking-[0.1em] uppercase flex items-center gap-1.5 mt-[2px]">
               Just now
            </p>
            <p className="text-white text-[11px] mt-1.5 leading-relaxed font-semibold">Waiting for math lecture notes to upload.</p>
          </div>
        </div>
      </div>

      {/* Upcoming Blocks Section (Issue 21) */}
      <div className="mt-4 pt-4 border-t border-white/5 pb-1">
        <div className="flex items-center justify-between mb-4 px-1">
          <h3 className="text-slate-500 text-[10px] font-extrabold uppercase tracking-[0.2em]">
            Upcoming Blocks
          </h3>
          <button className="text-slate-500 hover:text-white transition-colors bg-white/5 p-1 rounded-md hover:bg-white/10">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          </button>
        </div>
        
        <div className="space-y-2">
          {/* Active/Next Block */}
          <div className="flex items-center justify-between py-2.5 px-3 rounded-xl border border-[#36d3b7]/30 text-xs shadow-[0_0_15px_rgba(54,211,183,0.05)] bg-[#10121d]">
            <span className="font-extrabold text-[#36d3b7] w-[4.5rem]">3:00 PM</span>
            <span className="text-emerald-50 font-semibold flex-1 pl-3 border-l border-[#36d3b7]/20 truncate">Deep Work: CS 101</span>
            <span className="text-[#36d3b7]/80 font-bold text-[10px] shrink-0">2h</span>
          </div>
          
          {/* Future Block */}
          <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-[#121422] border border-white/5 text-xs hover:border-white/10 transition-colors">
            <span className="font-extrabold text-[#7364d9] w-[4.5rem]">6:30 PM</span>
            <span className="text-slate-300 font-semibold flex-1 pl-3 border-l border-white/10 truncate">Review BIO 200</span>
            <span className="text-slate-500 font-bold text-[10px] shrink-0">45m</span>
          </div>

          {/* Past/End Block */}
          <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-[#121422] border border-transparent text-xs opacity-60">
            <span className="font-extrabold text-slate-500 w-[4.5rem]">8:00 PM</span>
            <span className="text-slate-400 font-semibold flex-1 pl-3 border-l border-white/10 truncate">Free Time Guarded</span>
            <span className="text-slate-600 font-bold text-[10px] uppercase shrink-0">End</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
