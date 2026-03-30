import React from "react";

export default function DashboardPage() {
  return (
    <div className="h-full flex flex-col pt-3 pb-8 px-2 max-w-5xl mx-auto">
      <header className="mb-10 pl-2">
        <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-2">Main Content Area</h1>
        <p className="text-slate-400 text-xs font-semibold">Ready for Active Plan cards...</p>
      </header>

      <div className="flex-1 flex items-center justify-center border-2 border-dashed border-white/10 rounded-2xl bg-white/5">
         <p className="text-slate-500 font-medium">Dashboard center layout is ready!</p>
      </div>
    </div>
  );
}
