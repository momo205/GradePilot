import React from "react";

export default function RightSidebar() {
  return (
    <aside className="h-full w-72 bg-[#151421] border border-white/5 p-6 flex flex-col rounded-2xl shadow-xl">
      <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-sm border-2 border-dashed border-white/10 rounded-xl bg-white/5 text-center p-4">
        Right Sidebar Area
        <br />
        <span className="text-xs mt-2 opacity-75">(Agent Activity & Schedule coming soon)</span>
      </div>
    </aside>
  );
}
