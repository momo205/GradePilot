'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ChevronDown } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { listClasses, type ClassOut } from '@/lib/backend';

const DIFFICULTIES = ['Easy', 'Medium', 'Hard'];
const QUESTION_COUNTS = [3, 5, 10];

export default function PracticePage() {
  const router = useRouter();
  const [classes, setClasses] = useState<ClassOut[]>([]);
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [topic, setTopic] = useState('');
  const [difficulty, setDifficulty] = useState('Medium');
  const [count, setCount] = useState(5);

  useEffect(() => {
    listClasses()
      .then(setClasses)
      .finally(() => setLoadingClasses(false));
  }, []);

  const handleGenerate = () => {
    if (!topic.trim() || !selectedClassId) return;
    const params = new URLSearchParams({
      classId: selectedClassId,
      topic: topic.trim(),
      difficulty,
      count: String(count),
    });
    router.push(`/dashboard/practice/results?${params.toString()}`);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="pt-3 pb-12 px-2 max-w-[860px] mx-auto w-full"
    >
      <header className="mb-8 pl-2">
        <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-2 leading-none">
          Practice Generator
        </h1>
        <p className="text-slate-400 text-xs font-semibold tracking-wide">
          Select a class, enter a topic, and generate a practice set
        </p>
      </header>

      <div className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-6 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {/* Class */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Class</label>
            <div className="relative">
              <select
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(e.target.value)}
                disabled={loadingClasses}
                className="w-full appearance-none bg-black/30 border border-white/10 rounded-xl py-3 pl-4 pr-10 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all cursor-pointer disabled:opacity-50"
              >
                <option value="">{loadingClasses ? 'Loading...' : 'Select a class...'}</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {/* Topic */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Topic</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleGenerate(); }}
              placeholder='e.g. "Sorting Algorithms"'
              className="w-full bg-black/30 border border-white/10 rounded-xl py-3 px-4 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all"
            />
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Difficulty</label>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all border ${
                    difficulty === d
                      ? 'border-[#00F5D4]/50 bg-[#00F5D4]/10 text-[#00F5D4]'
                      : 'border-white/10 bg-black/20 text-slate-400 hover:text-white hover:border-white/20'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* # Questions */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Questions</label>
            <div className="flex gap-2">
              {QUESTION_COUNTS.map((n) => (
                <button
                  key={n}
                  onClick={() => setCount(n)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all border ${
                    count === n
                      ? 'border-[#6D4AFF]/50 bg-[#6D4AFF]/10 text-[#a78bfa]'
                      : 'border-white/10 bg-black/20 text-slate-400 hover:text-white hover:border-white/20'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={!selectedClassId || !topic.trim()}
          className="w-full py-3.5 rounded-xl font-extrabold text-sm text-[#0B0F2A] flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed shadow-[0_4px_20px_rgba(109,74,255,0.3)]"
          style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
        >
          <Sparkles className="w-4 h-4" />
          Generate Practice Set
        </button>
      </div>
    </motion.div>
  );
}
