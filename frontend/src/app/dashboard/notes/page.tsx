'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, ChevronRight, FileText, Clock, Inbox, Upload, X, Sparkles } from 'lucide-react';
import {
  listClasses,
  getClassNotes,
  addNotes,
  summariseDocument,
  type ClassOut,
  type NotesOut,
} from '@/lib/backend';

export default function NotesPage() {
  const [classes, setClasses] = useState<ClassOut[]>([]);
  const [selectedClass, setSelectedClass] = useState<ClassOut | null>(null);
  const [notes, setNotes] = useState<NotesOut[]>([]);
  const [selectedNote, setSelectedNote] = useState<NotesOut | null>(null);
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listClasses()
      .then((data) => {
        setClasses(data);
        if (data.length > 0) selectClass(data[0]);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load classes'))
      .finally(() => setLoadingClasses(false));
  }, []);

  const selectClass = async (cls: ClassOut) => {
    setSelectedClass(cls);
    setSelectedNote(null);
    setNotes([]);
    setUploadSuccess(false);
    setLoadingNotes(true);
    setError(null);
    try {
      const data = await getClassNotes(cls.id);
      setNotes(data);
      if (data.length > 0) setSelectedNote(data[0]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load notes');
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleFiles = async (files: File[]) => {
    if (!selectedClass || files.length === 0) return;
    setError(null);
    setUploadSuccess(false);
    setUploading(true);

    const textParts: string[] = [];
    for (const f of files) {
      const lower = f.name.toLowerCase();
      if (lower.endsWith('.txt') || lower.endsWith('.md')) {
        textParts.push(await f.text());
      } else {
        setError('Only .txt and .md files are supported.');
        setUploading(false);
        return;
      }
    }

    try {
      const filename = files.map((f) => f.name).join(', ');
      const result = await summariseDocument(filename, textParts.join('\n\n'));
      const saved = await addNotes(selectedClass.id, result.extracted_notes);
      setNotes((prev) => [saved, ...prev]);
      setSelectedNote(saved);
      setUploadSuccess(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save notes');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(Array.from(e.dataTransfer.files));
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
          My Notes
        </h1>
        <p className="text-slate-400 text-xs font-semibold tracking-wide">
          Browse and upload notes for each class
        </p>
      </header>

      {error && (
        <div className="mb-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 flex items-center justify-between gap-3">
          <span>{error}</span>
          <button onClick={() => setError(null)}><X className="w-4 h-4 shrink-0" /></button>
        </div>
      )}

      <div className="flex gap-4 flex-1 min-h-0">

        {/* Left — class list */}
        <div className="w-52 shrink-0 flex flex-col gap-2">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 pl-1 mb-1">Classes</p>
          {loadingClasses ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 rounded-xl bg-white/5 animate-pulse" />
            ))
          ) : classes.length === 0 ? (
            <p className="text-slate-500 text-xs pl-1">No classes yet.</p>
          ) : (
            classes.map((cls) => (
              <button
                key={cls.id}
                onClick={() => selectClass(cls)}
                className={`w-full flex items-center justify-between px-3 py-3 rounded-xl text-left text-sm font-semibold transition-all border ${
                  selectedClass?.id === cls.id
                    ? 'bg-[#00F5D4]/10 border-[#00F5D4]/30 text-[#00F5D4]'
                    : 'bg-white/[0.03] border-white/5 text-slate-300 hover:bg-white/[0.06] hover:text-white'
                }`}
              >
                <span className="truncate">{cls.title}</span>
                <ChevronRight className="w-3.5 h-3.5 shrink-0 opacity-50" />
              </button>
            ))
          )}
        </div>

        {/* Middle — notes list + upload */}
        <div className="w-52 shrink-0 flex flex-col gap-2">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 pl-1 mb-1">Saved Notes</p>

          {/* Upload dropzone — only shown when a class is selected */}
          {selectedClass && (
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative flex flex-col items-center justify-center gap-2 px-3 py-4 rounded-xl border-2 border-dashed cursor-pointer transition-all text-center mb-1 ${
                isDragging
                  ? 'border-[#00F5D4] bg-[#00F5D4]/10'
                  : 'border-white/10 bg-white/[0.02] hover:border-[#00F5D4]/40 hover:bg-[#00F5D4]/5'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md"
                multiple
                className="hidden"
                onChange={(e) => {
                  handleFiles(Array.from(e.target.files ?? []));
                  e.target.value = '';
                }}
              />
              {uploading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-[#00F5D4]/30 border-t-[#00F5D4] animate-spin" />
                  <p className="text-[10px] text-[#00F5D4] font-semibold">Gemini reading...</p>
                </>
              ) : uploadSuccess ? (
                <>
                  <Sparkles className="w-4 h-4 text-[#00F5D4]" />
                  <p className="text-[10px] text-[#00F5D4] font-semibold">Saved!</p>
                </>
              ) : (
                <>
                  <Upload className={`w-4 h-4 ${isDragging ? 'text-[#00F5D4]' : 'text-slate-500'}`} />
                  <p className={`text-[10px] font-semibold leading-tight ${isDragging ? 'text-[#00F5D4]' : 'text-slate-500'}`}>
                    Drop .txt/.md<br />to add notes
                  </p>
                </>
              )}
            </div>
          )}

          {loadingNotes ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse" />
            ))
          ) : !selectedClass ? (
            <p className="text-slate-500 text-xs pl-1">Select a class.</p>
          ) : notes.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-6 text-center">
              <Inbox className="w-6 h-6 text-slate-600" />
              <p className="text-slate-500 text-xs">No notes yet.<br />Drop a file above.</p>
            </div>
          ) : (
            notes.map((note, i) => (
              <button
                key={note.id}
                onClick={() => setSelectedNote(note)}
                className={`w-full flex flex-col gap-1 px-3 py-3 rounded-xl text-left transition-all border ${
                  selectedNote?.id === note.id
                    ? 'bg-[#6D4AFF]/10 border-[#6D4AFF]/30'
                    : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-[#6D4AFF] shrink-0" />
                  <span className={`text-xs font-bold truncate ${selectedNote?.id === note.id ? 'text-[#a78bfa]' : 'text-slate-300'}`}>
                    Note {notes.length - i}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 pl-5">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span className="text-[10px] text-slate-500">
                    {new Date(note.created_at).toLocaleDateString(undefined, {
                      month: 'short', day: 'numeric', year: 'numeric',
                    })}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Right — note content */}
        <div className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            {selectedNote ? (
              <motion.div
                key={selectedNote.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                className="h-full bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-6 flex flex-col shadow-[0_10px_40px_rgba(0,0,0,0.3)]"
              >
                <div className="flex items-center gap-2.5 mb-4 pb-4 border-b border-white/5">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
                  >
                    <BookOpen className="w-4 h-4 text-[#0B0F2A]" />
                  </div>
                  <div>
                    <p className="text-white text-sm font-extrabold">{selectedClass?.title}</p>
                    <p className="text-slate-400 text-[11px]">
                      Saved {new Date(selectedNote.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  <pre className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed font-sans">
                    {selectedNote.notes_text}
                  </pre>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-full flex flex-col items-center justify-center gap-3 bg-[#141B3A]/30 border-2 border-dashed border-white/5 rounded-[1.25rem]"
              >
                <BookOpen className="w-8 h-8 text-slate-600" />
                <p className="text-slate-500 text-sm font-semibold">
                  {selectedClass ? 'Select a note to read' : 'Select a class to get started'}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>
    </motion.div>
  );
}
