'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Eye, EyeOff, ArrowLeft, RefreshCw } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import { generatePractice, listClasses, type PracticeQuestion } from '@/lib/backend';
import Link from 'next/link';

export default function PracticeResultsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const classId = searchParams.get('classId') ?? '';
  const topic = searchParams.get('topic') ?? '';
  const difficulty = searchParams.get('difficulty') ?? 'Medium';
  const count = Number(searchParams.get('count') ?? 5);

  const [className, setClassName] = useState('');
  const [questions, setQuestions] = useState<PracticeQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const [allRevealed, setAllRevealed] = useState(false);

  const fetchQuestions = async () => {
    if (!classId || !topic) { router.push('/dashboard/practice'); return; }
    setLoading(true);
    setError(null);
    setRevealed(new Set());
    setAllRevealed(false);
    try {
      const [data, classes] = await Promise.all([
        generatePractice(classId, topic, count, difficulty),
        listClasses(),
      ]);
      setQuestions(data.questions);
      setClassName(classes.find((c) => c.id === classId)?.title ?? '');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to generate questions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchQuestions(); }, []);

  const toggleReveal = (i: number) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  const handleShowAll = () => {
    if (allRevealed) {
      setRevealed(new Set());
      setAllRevealed(false);
    } else {
      setRevealed(new Set(questions.map((_, i) => i)));
      setAllRevealed(true);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="pt-3 pb-12 px-2 max-w-[860px] mx-auto w-full"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-8 pl-2">
        <div>
          <Link
            href="/dashboard/practice"
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-3"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Practice Generator
          </Link>
          <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-1 leading-none">
            {topic}
          </h1>
          <p className="text-slate-400 text-xs font-semibold tracking-wide">
            {className && `${className} · `}{difficulty} · {count} questions
          </p>
        </div>
        <button
          onClick={fetchQuestions}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-all disabled:opacity-50 mt-6"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Regenerate
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-10 h-10 rounded-full border-2 border-[#00F5D4]/20 border-t-[#00F5D4] animate-spin" />
          <p className="text-slate-400 text-sm font-semibold">Generating questions with Gemini...</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="px-4 py-3 rounded-2xl border border-rose-500/20 bg-rose-500/10 text-sm text-rose-300 mb-4">
          {error}
        </div>
      )}

      {/* Questions */}
      {!loading && questions.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
        >
          <div className="flex items-center justify-between mb-4 pl-1">
            <p className="text-slate-400 text-xs font-semibold">
              {questions.length} question{questions.length !== 1 ? 's' : ''} generated
            </p>
            <button
              onClick={handleShowAll}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-all"
            >
              {allRevealed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {allRevealed ? 'Hide all answers' : 'Show all answers'}
            </button>
          </div>

          <div className="flex flex-col gap-3">
            {questions.map((q, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] overflow-hidden"
              >
                <button
                  onClick={() => toggleReveal(i)}
                  className="w-full flex items-start gap-4 p-5 text-left hover:bg-white/[0.02] transition-colors group"
                >
                  <span
                    className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-extrabold text-[#0B0F2A] mt-0.5"
                    style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
                  >
                    {i + 1}
                  </span>
                  <p className="flex-1 text-sm font-semibold text-white leading-relaxed">{q.q}</p>
                  <span className={`shrink-0 mt-0.5 transition-transform duration-200 ${revealed.has(i) ? 'rotate-180' : ''}`}>
                    <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-white" />
                  </span>
                </button>

                <AnimatePresence>
                  {revealed.has(i) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 pt-0 ml-11 border-t border-white/5">
                        <p className="text-[11px] font-bold uppercase tracking-widest text-[#00F5D4] mb-2 mt-3">Answer</p>
                        <p className="text-sm text-slate-300 leading-relaxed">{q.a}</p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
