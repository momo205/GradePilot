'use client';

import { motion } from 'framer-motion';
import { Bot, Calendar, FileUp, Sparkles, ArrowRight, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

const FEATURES = [
  {
    icon: <FileUp className="w-6 h-6" />,
    title: 'Smart Document Parsing',
    description: 'Upload syllabi, assignments, and notes. GradePilot extracts every deadline and task automatically.',
    color: 'text-[#00F5D4]',
    glow: 'shadow-[#00F5D4]/10',
    border: 'hover:border-[#00F5D4]/30',
  },
  {
    icon: <Sparkles className="w-6 h-6" />,
    title: 'AI-Generated Study Plans',
    description: 'A LangGraph agent prioritises your workload and builds a personalised, adaptive schedule around your life.',
    color: 'text-[#6D4AFF]',
    glow: 'shadow-[#6D4AFF]/10',
    border: 'hover:border-[#6D4AFF]/30',
  },
  {
    icon: <Calendar className="w-6 h-6" />,
    title: 'Google Calendar Sync',
    description: 'Study blocks are pushed directly to your calendar and automatically rescheduled when plans change.',
    color: 'text-[#00F5D4]',
    glow: 'shadow-[#00F5D4]/10',
    border: 'hover:border-[#00F5D4]/30',
  },
];

const SOCIAL_PROOF = [
  'Extracts deadlines from any PDF',
  'Adapts when you fall behind',
  'Syncs with Google Calendar',
  'Generates practice questions',
];

export default function LandingPage() {
  return (
    <div
      className="relative min-h-screen w-full text-[#F8FAFC] font-sans overflow-x-hidden"
      style={{ background: 'radial-gradient(ellipse at 50% 0%, #1a1f4a 0%, #0B0F2A 60%)' }}
    >
      {/* Background blobs */}
      <div className="pointer-events-none fixed top-[-10%] left-[-5%] w-[50%] h-[50%] bg-[#6D4AFF]/10 rounded-full blur-[140px]" />
      <div className="pointer-events-none fixed bottom-[-10%] right-[-5%] w-[50%] h-[50%] bg-[#00F5D4]/6 rounded-full blur-[160px]" />

      {/* ── Navbar ── */}
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-16 py-5 border-b border-white/5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-xl shadow-lg shadow-[#00F5D4]/20"
            style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
          >
            <Bot className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-[#94A3B8]">
            GradePilot
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-sm text-[#94A3B8] hover:text-white transition-colors hidden sm:block"
          >
            Dashboard
          </Link>
          <Link
            href="/auth"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-[#0B0F2A] transition-all hover:scale-105 active:scale-95"
            style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
          >
            Get Started <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-24 pb-20 md:pt-36 md:pb-28">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#00F5D4]/20 bg-[#00F5D4]/5 text-[#00F5D4] text-xs font-semibold mb-8 tracking-wide"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Powered by Gemini 1.5 Pro + LangGraph
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.08] max-w-4xl"
        >
          Your autonomous{' '}
          <span className="bg-clip-text text-transparent" style={{ backgroundImage: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}>
            academic co-pilot
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-6 text-lg md:text-xl text-[#94A3B8] max-w-2xl leading-relaxed"
        >
          Upload your course materials and let GradePilot extract every deadline, build a personalised study plan, and keep your Google Calendar in sync — automatically.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="mt-10 flex flex-col sm:flex-row items-center gap-4"
        >
          <Link
            href="/auth"
            className="flex items-center gap-2 px-7 py-3.5 rounded-2xl text-base font-bold text-[#0B0F2A] shadow-[0_4px_30px_rgba(109,74,255,0.35)] hover:shadow-[0_4px_40px_rgba(0,245,212,0.4)] transition-all hover:scale-105 active:scale-95"
            style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
          >
            Start Planning Free <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="/auth"
            className="px-7 py-3.5 rounded-2xl text-base font-semibold text-[#94A3B8] border border-white/10 hover:border-white/20 hover:text-white transition-all"
          >
            Sign In
          </Link>
        </motion.div>

        {/* Social proof pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-12 flex flex-wrap justify-center gap-3"
        >
          {SOCIAL_PROOF.map((item) => (
            <span
              key={item}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/8 text-xs text-[#94A3B8]"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-[#00F5D4]" />
              {item}
            </span>
          ))}
        </motion.div>
      </section>

      {/* ── Features ── */}
      <section className="relative z-10 px-6 md:px-16 pb-28 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-14"
        >
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Everything handled by the agent
          </h2>
          <p className="text-[#94A3B8] text-base max-w-xl mx-auto">
            GradePilot runs autonomously in the background so you can focus on actually learning.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className={`flex flex-col p-7 rounded-3xl bg-[#141B3A]/60 border border-white/5 backdrop-blur-md shadow-xl ${f.glow} ${f.border} transition-all duration-300`}
            >
              <div className={`w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-5 ${f.color}`}>
                {f.icon}
              </div>
              <h3 className="text-lg font-bold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-[#94A3B8] leading-relaxed">{f.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="relative z-10 px-6 md:px-16 pb-28 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative flex flex-col items-center text-center p-12 rounded-3xl border border-white/5 overflow-hidden"
          style={{ background: 'linear-gradient(135deg, rgba(109,74,255,0.15), rgba(0,245,212,0.08))' }}
        >
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-[#6D4AFF]/10 to-[#00F5D4]/5" />
          <Bot className="w-12 h-12 text-[#00F5D4] mb-5 drop-shadow-[0_0_20px_rgba(0,245,212,0.5)]" />
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Ready to stop stressing about deadlines?
          </h2>
          <p className="text-[#94A3B8] text-base mb-8 max-w-lg">
            Join students who let GradePilot handle the planning while they focus on learning.
          </p>
          <Link
            href="/auth"
            className="flex items-center gap-2 px-8 py-4 rounded-2xl text-base font-bold text-[#0B0F2A] shadow-[0_4px_30px_rgba(0,245,212,0.3)] hover:shadow-[0_4px_40px_rgba(0,245,212,0.5)] transition-all hover:scale-105 active:scale-95"
            style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
          >
            Launch GradePilot <ArrowRight className="w-5 h-5" />
          </Link>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-white/5 px-6 md:px-16 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#94A3B8]">
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
          >
            <Bot className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold text-white">GradePilot</span>
          <span>— Autonomous Academic Planning Agent</span>
        </div>
        <span>© {new Date().getFullYear()} GradePilot. All rights reserved.</span>
      </footer>
    </div>
  );
}
