'use client';

import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, FileText, Sparkles, Upload, X } from 'lucide-react';

const MOCK_CLASSES = [
  { id: 'cs101', title: 'CS 101: Data Structures' },
  { id: 'bio200', title: 'BIO 200: Genetics' },
  { id: 'math220', title: 'MATH 220: Linear Algebra' },
  { id: 'eng150', title: 'ENG 150: Rhetoric' },
];

const MOCK_TOPICS_BY_CLASS: Record<string, string[]> = {
  cs101: ['Arrays & Linked Lists', 'Stacks & Queues', 'Hash Tables', 'Binary Trees', 'Graph Traversal'],
  bio200: ['Mendelian Inheritance', 'DNA Replication', 'Gene Expression', 'Mutations', 'Population Genetics'],
  math220: ['Vector Spaces', 'Matrix Operations', 'Determinants', 'Eigenvalues', 'Orthogonality'],
  eng150: ['Thesis Construction', 'Ethos, Pathos, Logos', 'Counterargument', 'Citation Styles', 'Revision Strategy'],
};

export default function MaterialsPage() {
  const [selectedClassId, setSelectedClassId] = useState<string>(MOCK_CLASSES[0].id);
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [topics, setTopics] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedClass = MOCK_CLASSES.find((c) => c.id === selectedClassId);

  const addFiles = (incoming: File[]) => {
    if (incoming.length === 0) return;
    setFiles((prev) => [...prev, ...incoming]);
    setTopics([]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setTopics([]);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  };

  const extractTopics = () => {
    if (files.length === 0) return;
    setExtracting(true);
    setTopics([]);
    setTimeout(() => {
      setTopics(MOCK_TOPICS_BY_CLASS[selectedClassId] ?? []);
      setExtracting(false);
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
          Materials
        </h1>
        <p className="text-slate-400 text-xs font-semibold tracking-wide">
          Upload course files and let the agent extract topics
        </p>
      </header>

      <div className="flex flex-col gap-4 flex-1 min-h-0">
        <div className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-2">
            <BookOpen className="w-3 h-3" /> Select Class
          </label>
          <select
            value={selectedClassId}
            onChange={(e) => {
              setSelectedClassId(e.target.value);
              setTopics([]);
            }}
            className="w-full bg-[#0B0F2A] border border-white/10 rounded-xl px-4 py-3 text-sm font-semibold text-white focus:outline-none focus:border-[#00F5D4]/50 focus:ring-1 focus:ring-[#00F5D4]/50 transition-all"
          >
            {MOCK_CLASSES.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-3 px-6 py-10 rounded-[1.25rem] border-2 border-dashed cursor-pointer transition-all text-center ${
            isDragging
              ? 'border-[#00F5D4] bg-[#00F5D4]/10'
              : 'border-white/10 bg-[#141B3A]/30 hover:border-[#00F5D4]/40 hover:bg-[#00F5D4]/5'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              addFiles(Array.from(e.target.files ?? []));
              e.target.value = '';
            }}
          />
          <Upload className={`w-6 h-6 ${isDragging ? 'text-[#00F5D4]' : 'text-slate-500'}`} />
          <div>
            <p className={`text-sm font-bold ${isDragging ? 'text-[#00F5D4]' : 'text-white'}`}>
              Drop files here or click to browse
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Syllabi, slides, PDFs &mdash; {selectedClass?.title}
            </p>
          </div>
        </div>

        <AnimatePresence>
          {files.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5"
            >
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-3">
                Selected Files ({files.length})
              </p>
              <div className="flex flex-col gap-2">
                {files.map((file, i) => (
                  <motion.div
                    key={`${file.name}-${i}`}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/5"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-4 h-4 text-[#6D4AFF] shrink-0" />
                      <span className="text-sm font-semibold text-slate-200 truncate">{file.name}</span>
                      <span className="text-[10px] text-slate-500 shrink-0">
                        {(file.size / 1024).toFixed(1)} KB
                      </span>
                    </div>
                    <button
                      onClick={() => removeFile(i)}
                      className="p-1 text-slate-500 hover:text-rose-400 transition-colors shrink-0"
                      aria-label="Remove file"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <button
          onClick={extractTopics}
          disabled={files.length === 0 || extracting}
          className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#6D4AFF] to-[#00F5D4] text-black font-extrabold text-sm shadow-[0_4px_25px_rgba(0,245,212,0.25)] hover:shadow-[0_4px_30px_rgba(0,245,212,0.45)] transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
        >
          {extracting ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-black/30 border-t-black animate-spin" />
              Extracting topics...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Extract Topics
            </>
          )}
        </button>

        <AnimatePresence>
          {topics.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="bg-[#141B3A]/50 backdrop-blur-xl border border-[#00F5D4]/20 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]"
            >
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-[#00F5D4]" />
                <p className="text-[11px] font-bold uppercase tracking-widest text-[#00F5D4]">
                  Extracted Topics
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {topics.map((topic, i) => (
                  <motion.span
                    key={topic}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.07 }}
                    className="px-3.5 py-2 rounded-full bg-[#00F5D4]/10 border border-[#00F5D4]/30 text-[#00F5D4] text-xs font-bold"
                  >
                    {topic}
                  </motion.span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
