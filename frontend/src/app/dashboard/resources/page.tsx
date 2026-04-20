'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, ExternalLink, Layers, Sparkles } from 'lucide-react';
import { MOCK_CLASSES, MOCK_TOPICS_BY_CLASS } from '@/lib/mockCourseData';

type Resource = { title: string; url: string; source: string; description: string };

const buildMockResources = (classTitle: string, topic: string): Resource[] => [
  {
    title: `${topic} — Crash Course`,
    url: 'https://example.com/crash-course',
    source: 'YouTube',
    description: `A 12-minute overview of ${topic.toLowerCase()} with worked examples.`,
  },
  {
    title: `${topic}: A Beginner's Guide`,
    url: 'https://example.com/beginners-guide',
    source: 'Khan Academy',
    description: `Step-by-step lessons covering the fundamentals of ${topic.toLowerCase()}.`,
  },
  {
    title: `Practice Problems — ${topic}`,
    url: 'https://example.com/practice',
    source: 'Brilliant',
    description: `30 graded practice problems for ${classTitle}.`,
  },
  {
    title: `${classTitle}: Lecture Notes on ${topic}`,
    url: 'https://example.com/lecture-notes',
    source: 'MIT OCW',
    description: 'Full lecture notes plus problem set with solutions.',
  },
  {
    title: `Visual Explainer: ${topic}`,
    url: 'https://example.com/visual',
    source: '3Blue1Brown',
    description: `Animated walkthrough that builds intuition for ${topic.toLowerCase()}.`,
  },
];

export default function ResourcesPage() {
  const [selectedClassId, setSelectedClassId] = useState<string>(MOCK_CLASSES[0].id);
  const [selectedTopic, setSelectedTopic] = useState<string>(MOCK_TOPICS_BY_CLASS[MOCK_CLASSES[0].id][0]);
  const [loading, setLoading] = useState(false);
  const [resources, setResources] = useState<Resource[]>([]);
  const recommendTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const classSelectId = useId();
  const topicSelectId = useId();

  const selectedClass = MOCK_CLASSES.find((c) => c.id === selectedClassId);
  const topicsForClass = MOCK_TOPICS_BY_CLASS[selectedClassId] ?? [];

  useEffect(() => {
    return () => {
      if (recommendTimeoutRef.current) clearTimeout(recommendTimeoutRef.current);
    };
  }, []);

  const cancelPending = () => {
    if (recommendTimeoutRef.current) {
      clearTimeout(recommendTimeoutRef.current);
      recommendTimeoutRef.current = null;
    }
    setLoading(false);
  };

  const handleClassChange = (id: string) => {
    cancelPending();
    setSelectedClassId(id);
    setSelectedTopic(MOCK_TOPICS_BY_CLASS[id]?.[0] ?? '');
    setResources([]);
  };

  const handleTopicChange = (topic: string) => {
    cancelPending();
    setSelectedTopic(topic);
    setResources([]);
  };

  const recommend = () => {
    if (!selectedClass || !selectedTopic) return;
    cancelPending();
    setLoading(true);
    setResources([]);
    const targetClass = selectedClass.title;
    const targetTopic = selectedTopic;
    recommendTimeoutRef.current = setTimeout(() => {
      setResources(buildMockResources(targetClass, targetTopic));
      setLoading(false);
      recommendTimeoutRef.current = null;
    }, 900);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="pt-3 pb-12 px-2 max-w-[1000px] mx-auto w-full h-full flex flex-col"
    >
      <header className="mb-6 pl-2">
        <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-1 leading-none">
          Resources
        </h1>
        <p className="text-slate-400 text-xs font-semibold tracking-wide">
          Pick a class and topic, then let the agent recommend study links
        </p>
      </header>

      <div className="flex flex-col gap-4 flex-1 min-h-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
            <label
              htmlFor={classSelectId}
              className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-2"
            >
              <BookOpen className="w-3 h-3" /> Select Class
            </label>
            <select
              id={classSelectId}
              value={selectedClassId}
              onChange={(e) => handleClassChange(e.target.value)}
              className="w-full bg-[#0B0F2A] border border-white/10 rounded-xl px-4 py-3 text-sm font-semibold text-white focus:outline-none focus:border-[#00F5D4]/50 focus:ring-1 focus:ring-[#00F5D4]/50 transition-all"
            >
              {MOCK_CLASSES.map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          </div>

          <div className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
            <label
              htmlFor={topicSelectId}
              className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-2"
            >
              <Layers className="w-3 h-3" /> Select Topic
            </label>
            <select
              id={topicSelectId}
              value={selectedTopic}
              onChange={(e) => handleTopicChange(e.target.value)}
              className="w-full bg-[#0B0F2A] border border-white/10 rounded-xl px-4 py-3 text-sm font-semibold text-white focus:outline-none focus:border-[#6D4AFF]/50 focus:ring-1 focus:ring-[#6D4AFF]/50 transition-all"
            >
              {topicsForClass.map((topic) => (
                <option key={topic} value={topic}>{topic}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={recommend}
          disabled={loading || !selectedTopic}
          className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#6D4AFF] to-[#00F5D4] text-black font-extrabold text-sm shadow-[0_4px_25px_rgba(0,245,212,0.25)] hover:shadow-[0_4px_30px_rgba(0,245,212,0.45)] transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none focus:outline-none focus:ring-2 focus:ring-[#00F5D4]/60"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-black/30 border-t-black animate-spin" />
              Finding resources...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Recommend
            </>
          )}
        </button>

        <AnimatePresence>
          {resources.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="bg-[#141B3A]/50 backdrop-blur-xl border border-[#00F5D4]/20 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]"
            >
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-[#00F5D4]" />
                <p className="text-[11px] font-bold uppercase tracking-widest text-[#00F5D4]">
                  Recommended for {selectedTopic}
                </p>
              </div>
              <ul className="flex flex-col gap-3">
                {resources.map((r, i) => (
                  <motion.li
                    key={r.url}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.06 }}
                  >
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-start justify-between gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-[#00F5D4]/40 hover:bg-[#00F5D4]/5 transition-all focus:outline-none focus:ring-2 focus:ring-[#00F5D4]/60"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-white truncate group-hover:text-[#00F5D4] transition-colors">
                          {r.title}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{r.description}</p>
                        <p className="text-[10px] uppercase tracking-widest text-[#6D4AFF] font-bold mt-1.5">
                          {r.source}
                        </p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-[#00F5D4] transition-colors shrink-0 mt-1" />
                    </a>
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
