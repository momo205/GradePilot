"use client";

import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  addNotes,
  createClass,
  createStudyPlan,
  type ClassOut,
  type NotesOut,
  type StudyPlanOut,
} from "@/lib/backend";
import UploadHub from "@/components/dashboard/UploadHub";

export default function DashboardPage() {
  const [classTitle, setClassTitle] = useState("");
  const [notesText, setNotesText] = useState("");
  const [clazz, setClazz] = useState<ClassOut | null>(null);
  const [notes, setNotes] = useState<NotesOut | null>(null);
  const [plan, setPlan] = useState<StudyPlanOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canCreateClass = classTitle.trim().length > 0;
  const canSubmitNotes = Boolean(clazz) && notesText.trim().length > 0;
  const canGeneratePlan = Boolean(clazz) && Boolean(notes);

  const schedule = useMemo(() => plan?.plan_json?.schedule ?? [], [plan]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.1, ease: "easeOut" }}
      className="h-full flex flex-col pt-3 pb-8 px-2 max-w-[1000px] mx-auto w-full z-10 relative"
    >
      <header className="flex items-center justify-between mb-10 pl-2">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-2 leading-none">
            Create a Study Plan
          </h1>
          <p className="text-slate-400 text-xs font-semibold tracking-wide">
            Add your class notes/syllabus and generate a plan
          </p>
        </div>
        {plan ? (
          <div className="flex items-center gap-2.5 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-bold shadow-inner shadow-emerald-500/10 backdrop-blur-md">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            Plan Generated
          </div>
        ) : null}
      </header>

      {error ? (
        <div className="mb-6 mx-2 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch pb-6">
        <motion.div 
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ duration: 0.5, delay: 0.2 }}
           whileHover={{ y: -4, transition: { duration: 0.2 } }}
           className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-7 shadow-[0_10px_40px_rgba(0,0,0,0.3)] group hover:border-[#7364d9]/40 transition-all duration-300 flex flex-col relative overflow-hidden min-h-[280px]"
        >
          <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#7364d9]/10 to-transparent pointer-events-none opacity-40"></div>
          
          <h2 className="text-lg font-extrabold text-white mb-6 tracking-wide relative z-10">
            1) Add your class
          </h2>
          
          <div className="space-y-4 mb-8 flex-1 relative z-10">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                Class title
              </label>
              <input
                value={classTitle}
                onChange={(e) => setClassTitle(e.target.value)}
                placeholder='e.g. "CS 101: Data Structures"'
                className="mt-2 w-full bg-black/30 border border-white/10 rounded-xl py-3 px-4 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all"
              />
            </div>

            <div className="text-xs text-slate-400">
              {clazz ? (
                <span>
                  Using class: <span className="text-white font-semibold">{clazz.title}</span>
                </span>
              ) : (
                <span>Creates a class row in Supabase.</span>
              )}
            </div>
          </div>
          
          <button
            disabled={!canCreateClass || loading}
            onClick={async () => {
              setError(null);
              setLoading(true);
              try {
                const created = await createClass(classTitle.trim());
                setClazz(created);
                setNotes(null);
                setPlan(null);
              } catch (e: any) {
                setError(e?.message ?? "Failed to create class");
              } finally {
                setLoading(false);
              }
            }}
            className="relative z-10 w-full mt-auto py-3.5 rounded-xl bg-gradient-to-r from-[#7364d9] to-[#62EBD0] text-black font-extrabold text-sm shadow-[0_4px_20px_rgba(54,211,183,0.2)] hover:shadow-[0_4px_25px_rgba(54,211,183,0.4)] transition-all flex items-center justify-center gap-2 group/btn disabled:opacity-60 disabled:cursor-not-allowed"
          >
            Create class
          </button>
        </motion.div>

        <motion.div 
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ duration: 0.5, delay: 0.3 }}
           whileHover={{ y: -4, transition: { duration: 0.2 } }}
           className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-7 shadow-[0_10px_40px_rgba(0,0,0,0.3)] group hover:border-[#7364d9]/40 transition-all duration-300 flex flex-col relative overflow-hidden min-h-[280px]"
        >
          <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#36d3b7]/10 to-transparent pointer-events-none opacity-40"></div>
          
          <h2 className="text-lg font-extrabold text-white mb-6 tracking-wide relative z-10">
            2) Drag & drop notes / syllabus
          </h2>
          
          <div className="space-y-4 mb-8 flex-1 relative z-10">
            <UploadHub
              title="Upload notes"
              subtitle="Drop .txt/.md/.pdf (we extract text from txt/md for now)"
              accept=".txt,.md,.pdf"
              multiple={true}
              onFilesSelected={async (files) => {
                setError(null);
                const textParts: string[] = [];
                for (const f of files) {
                  const lower = f.name.toLowerCase();
                  if (lower.endsWith(".txt") || lower.endsWith(".md")) {
                    textParts.push(`--- ${f.name} ---\n${await f.text()}`);
                  } else if (lower.endsWith(".pdf")) {
                    textParts.push(`--- ${f.name} ---\n[PDF uploaded: text extraction not implemented yet]`);
                  } else {
                    textParts.push(`--- ${f.name} ---\n[Unsupported file type]`);
                  }
                }
                setNotesText((prev) => (prev ? `${prev}\n\n${textParts.join("\n\n")}` : textParts.join("\n\n")));
              }}
            />
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                Extracted text preview
              </p>
              <pre className="whitespace-pre-wrap text-xs text-slate-200 max-h-32 overflow-y-auto custom-scrollbar">
                {notesText || "Drop a .txt/.md file to populate notes here."}
              </pre>
            </div>
            <div className="text-xs text-slate-400">
              {notes ? (
                <span>
                  Notes saved: <span className="text-white font-semibold">{new Date(notes.created_at).toLocaleString()}</span>
                </span>
              ) : (
                <span>Stores notes in Supabase for the selected class.</span>
              )}
            </div>
          </div>
          
          <button
            disabled={!canSubmitNotes || loading}
            onClick={async () => {
              if (!clazz) return;
              setError(null);
              setLoading(true);
              try {
                const created = await addNotes(clazz.id, notesText.trim());
                setNotes(created);
                setPlan(null);
              } catch (e: any) {
                setError(e?.message ?? "Failed to save notes");
              } finally {
                setLoading(false);
              }
            }}
            className="relative z-10 w-full mt-auto py-3.5 rounded-xl bg-gradient-to-r from-[#7364d9] to-[#62EBD0] text-black font-extrabold text-sm shadow-[0_4px_20px_rgba(54,211,183,0.2)] hover:shadow-[0_4px_25px_rgba(54,211,183,0.4)] transition-all flex items-center justify-center gap-2 group/btn disabled:opacity-60 disabled:cursor-not-allowed"
          >
            Save notes
          </button>
        </motion.div>

        <motion.div 
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ duration: 0.5, delay: 0.4 }}
           whileHover={{ y: -4, transition: { duration: 0.2 } }}
           className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-7 shadow-[0_10px_40px_rgba(0,0,0,0.3)] group hover:border-[#7364d9]/40 transition-all duration-300 flex flex-col relative overflow-hidden min-h-[280px]"
        >
          <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white/5 to-transparent pointer-events-none opacity-40"></div>
          
          <h2 className="text-lg font-extrabold text-white mb-6 tracking-wide relative z-10">
            3) Generate plan
          </h2>
          
          <div className="space-y-3 mb-8 flex-1 relative z-10">
            {plan ? (
              <>
                <p className="text-white text-sm font-extrabold">{plan.plan_json.title}</p>
                <div className="flex flex-wrap gap-2">
                  {plan.plan_json.goals?.slice(0, 4).map((g) => (
                    <span
                      key={g}
                      className="text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full bg-white/5 border border-white/10 text-slate-300"
                    >
                      {g}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-slate-400 text-sm">
                This calls the backend AI endpoint and stores the plan in Supabase.
              </p>
            )}
          </div>
          
          <button
            disabled={!canGeneratePlan || loading}
            onClick={async () => {
              if (!clazz || !notes) return;
              setError(null);
              setLoading(true);
              try {
                const created = await createStudyPlan(clazz.id, notes.id);
                setPlan(created);
              } catch (e: any) {
                setError(e?.message ?? "Failed to generate plan");
              } finally {
                setLoading(false);
              }
            }}
            className="relative z-10 w-full mt-auto py-3.5 rounded-xl bg-gradient-to-r from-[#7364d9] to-[#62EBD0] text-black font-extrabold text-sm shadow-[0_4px_20px_rgba(54,211,183,0.2)] hover:shadow-[0_4px_25px_rgba(54,211,183,0.4)] transition-all flex items-center justify-center gap-2 group/btn disabled:opacity-60 disabled:cursor-not-allowed"
          >
            Generate study plan
          </button>
        </motion.div>

        <motion.div 
           initial={{ opacity: 0, scale: 0.95 }}
           animate={{ opacity: 1, scale: 1 }}
           transition={{ duration: 0.5, delay: 0.6 }}
           className="bg-transparent border-2 border-dashed border-white/5 hover:border-[#36d3b7]/20 hover:bg-[#36d3b7]/[0.02] transition-colors rounded-[1.25rem] p-7 flex flex-col items-center justify-center gap-4 text-center min-h-[280px]"
        >
          <div className="w-12 h-12 rounded-full border border-white/5 bg-white/5 flex items-center justify-center">
            <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
          </div>
          {plan ? (
            <div className="w-full text-left">
              <p className="text-slate-400 text-[10px] uppercase tracking-widest font-bold mb-3">
                Schedule
              </p>
              <div className="space-y-3 max-h-56 overflow-y-auto pr-1 custom-scrollbar">
                {schedule.map((d) => (
                  <div
                    key={d.day}
                    className="rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <p className="text-white text-sm font-extrabold mb-2">{d.day}</p>
                    <ul className="space-y-1.5">
                      {d.tasks.map((t) => (
                        <li key={t} className="text-slate-300 text-xs">
                          - {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-slate-500 text-[11px] uppercase tracking-widest font-bold">
              Generate a plan to see the schedule
            </p>
          )}
        </motion.div>

      </div>
    </motion.div>
  );
}
