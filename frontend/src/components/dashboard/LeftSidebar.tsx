import React from "react";
import UploadHub from "./UploadHub";

export default function LeftSidebar() {
  return (
    <aside className="h-full w-[300px] bg-[#161825]/95 border border-white/5 p-6 flex flex-col rounded-3xl shadow-xl shadow-black/30 relative">
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
      <div className="mt-auto pt-6 flex flex-col gap-3.5 pl-1">
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
    </aside>
  );
}
