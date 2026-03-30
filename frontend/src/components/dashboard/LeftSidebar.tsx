import React from "react";
import UploadHub from "./UploadHub";

export default function LeftSidebar() {
  return (
    <aside className="h-full w-64 bg-[#151421] border border-white/5 p-6 flex flex-col rounded-2xl shadow-xl">
      {/* Brand Header placeholder */}
      <div className="mb-6">
        <h1 className="text-white font-extrabold text-lg">GradePilot</h1>
        <p className="text-cyan-400/80 text-[9px] uppercase font-bold mt-1">Autonomous Agent</p>
      </div>

      <UploadHub />
    </aside>
  );
}
