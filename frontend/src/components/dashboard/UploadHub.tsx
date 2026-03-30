"use client";

import React, { useState } from "react";

export default function UploadHub() {
  const [isDragging, setIsDragging] = useState(false);
  const [fileList, setFileList] = useState<File[]>([]);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFileList((prev) => [...prev, ...droppedFiles]);
    }
  };

  const removeFile = (indexToRemove: number) => {
    setFileList((prev) => prev.filter((_, i) => i !== indexToRemove));
  };

  return (
    <div className="flex-1 flex flex-col mt-4">
      <h2 className="text-slate-400 text-[10px] font-bold mb-4 uppercase tracking-[0.2em] flex items-center gap-2">
        <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        Upload Hub
      </h2>

      {/* Dropzone Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative flex flex-col items-center justify-center text-center p-4 rounded-xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden ${
          isDragging
            ? "border-cyan-400 bg-cyan-400/10 scale-[1.02]"
            : "border-white/10 bg-white/5 hover:border-cyan-400/50 hover:bg-cyan-400/5 group"
        }`}
        style={{ minHeight: "160px" }}
      >
        <div className={`absolute inset-0 bg-gradient-to-b from-transparent to-indigo-500/5 transition-opacity ${isDragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}></div>
        
        <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-3 transition-transform duration-300 shadow-lg border relative z-10 ${
          isDragging 
            ? "bg-cyan-500/20 text-cyan-400 border-cyan-400 -translate-y-1" 
            : "bg-slate-800/80 text-slate-300 border-white/5 group-hover:text-cyan-400 group-hover:border-cyan-400/30 group-hover:-translate-y-1"
        }`}>
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        
        <p className="text-slate-200 text-sm font-semibold relative z-10 transition-colors">
          {isDragging ? "Drop Files Here!" : "Drag & Drop to Pilot"}
        </p>
        <p className="text-slate-500 text-[11px] mt-1.5 max-w-[140px] leading-relaxed relative z-10">
          Syllabi, PDFs, or Notes
        </p>

        {/* Hidden file input for clicking support later */}
        <input type="file" multiple className="hidden" />
      </div>

      {/* File List Preview */}
      {fileList.length > 0 && (
        <div className="mt-4 flex-1 flex flex-col min-h-0">
          <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider pl-1 mb-2 shrink-0">Pending Uploads ({fileList.length})</p>
          <ul className="space-y-2 overflow-y-auto custom-scrollbar pr-1 flex-1">
            {fileList.map((file, idx) => (
              <li key={idx} className="flex items-center justify-between bg-[#0B0B11] border border-white/10 rounded-lg py-2 px-3 group transition-colors hover:border-white/20">
                <div className="flex items-center gap-2 overflow-hidden">
                  <svg className="w-3.5 h-3.5 text-indigo-400 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" /></svg>
                  <span className="text-xs text-slate-300 truncate">{file.name}</span>
                </div>
                <button
                  onClick={() => removeFile(idx)}
                  className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
