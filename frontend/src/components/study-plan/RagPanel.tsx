import React from 'react';
import type { ClassAskOut, MaterialIngestOut } from '@/lib/backend';

const DOC_TYPES = ['syllabus', 'reading', 'assignment', 'notes'] as const;

export function RagPanel({
  loading,
  ingestResult,
  askResult,
  question,
  onQuestionChange,
  uploadDocType,
  onUploadDocTypeChange,
  askDocTypeFilter,
  onAskDocTypeFilterChange,
  pasteToIndex,
  onPasteToIndexChange,
  onUploadPdf,
  onIndexPastedText,
  onAsk,
}: {
  loading: boolean;
  ingestResult: MaterialIngestOut | null;
  askResult: ClassAskOut | null;
  question: string;
  onQuestionChange: (v: string) => void;
  uploadDocType: string;
  onUploadDocTypeChange: (v: string) => void;
  askDocTypeFilter: string;
  onAskDocTypeFilterChange: (v: string) => void;
  pasteToIndex: string;
  onPasteToIndexChange: (v: string) => void;
  onUploadPdf: (file: File) => void;
  onIndexPastedText: () => void;
  onAsk: () => void;
}) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">Ask the course</h2>
        <p className="text-sm text-slate-300">
          Index a syllabus or reading (PDF or pasted text), then ask questions grounded in those
          materials. Answers include source snippets.
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
        <div>
          <p className="text-sm font-medium text-slate-200">1. Index materials</p>
          <p className="text-xs text-slate-400 mt-1">
            Upload a PDF or paste text below. This is separate from “Notes” — it powers search and
            Q&amp;A.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1">
            <label className="text-xs text-slate-400">Document type</label>
            <select
              value={uploadDocType}
              onChange={(e) => onUploadDocTypeChange(e.target.value)}
              className="bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm min-w-[140px]"
            >
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <label className="text-sm text-slate-300 hover:text-white cursor-pointer rounded-xl border border-white/15 bg-white/[0.03] px-4 py-2">
            <input
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = '';
                if (f) onUploadPdf(f);
              }}
            />
            Upload PDF
          </label>
        </div>

        <div className="space-y-2">
          <label className="text-xs text-slate-400">Or paste text to index</label>
          <textarea
            value={pasteToIndex}
            onChange={(e) => onPasteToIndexChange(e.target.value)}
            placeholder="Paste syllabus or reading text here, then click Index text."
            className="w-full min-h-[100px] bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-white/20"
          />
          <div className="flex justify-end">
            <button
              type="button"
              disabled={loading || pasteToIndex.trim().length === 0}
              onClick={onIndexPastedText}
              className="rounded-xl border border-white/15 bg-white/[0.03] text-slate-100 px-4 py-2 text-sm font-semibold hover:bg-white/[0.06] disabled:opacity-60"
            >
              Index text
            </button>
          </div>
        </div>

        {ingestResult ? (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">
            Indexed: <span className="font-mono">{ingestResult.document_id}</span> —{' '}
            {ingestResult.chunks_created} chunk{ingestResult.chunks_created === 1 ? '' : 's'}
          </div>
        ) : null}

        <div className="border-t border-white/10 pt-4 space-y-3">
          <p className="text-sm font-medium text-slate-200">2. Ask a question</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div className="md:col-span-2">
              <textarea
                value={question}
                onChange={(e) => onQuestionChange(e.target.value)}
                placeholder='e.g. "What are the grading weights?"'
                className="w-full min-h-[88px] bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-white/20"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Filter by type (optional)</label>
              <select
                value={askDocTypeFilter}
                onChange={(e) => onAskDocTypeFilterChange(e.target.value)}
                className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-sm"
              >
                <option value="">All indexed types</option>
                {DOC_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              disabled={loading || question.trim().length === 0}
              onClick={onAsk}
              className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              Ask
            </button>
          </div>
        </div>

        {askResult ? (
          <div className="rounded-xl border border-white/10 bg-black/20 p-3 space-y-3">
            <p className="text-xs font-medium text-slate-300">Answer</p>
            <p className="text-sm text-slate-100 whitespace-pre-wrap">{askResult.answer}</p>
            {askResult.sources.length > 0 ? (
              <div>
                <p className="text-xs font-medium text-slate-300 mb-2">Sources</p>
                <ul className="space-y-2">
                  {askResult.sources.map((s, i) => (
                    <li
                      key={`${s.document_id}-${s.chunk_index}-${i}`}
                      className="text-xs text-slate-400 border-l-2 border-white/20 pl-3"
                    >
                      <span className="text-slate-300">{s.filename}</span> ({s.document_type}, chunk{' '}
                      {s.chunk_index})
                      <div className="mt-1 text-slate-300">{s.snippet}</div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
