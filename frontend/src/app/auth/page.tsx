'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Mail, Lock, User, ArrowRight, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

type Mode = 'signin' | 'signup';

export default function AuthPage() {
  const router = useRouter();
  const supabase = createClient();

  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    if (mode === 'signup') {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { full_name: name } },
      });
      if (error) {
        setError(error.message);
      } else {
        setMessage('Check your email to confirm your account.');
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setError(error.message);
      } else {
        router.push('/dashboard');
        router.refresh();
      }
    }

    setLoading(false);
  };

  return (
    <div
      className="relative min-h-screen w-full flex items-center justify-center text-[#F8FAFC] font-sans px-4"
      style={{ background: 'radial-gradient(ellipse at 50% 0%, #1a1f4a 0%, #0B0F2A 60%)' }}
    >
      {/* Background blobs */}
      <div className="pointer-events-none fixed top-[-10%] left-[-5%] w-[50%] h-[50%] bg-[#6D4AFF]/10 rounded-full blur-[140px]" />
      <div className="pointer-events-none fixed bottom-[-10%] right-[-5%] w-[50%] h-[50%] bg-[#00F5D4]/6 rounded-full blur-[160px]" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 justify-center mb-8">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-xl shadow-lg shadow-[#00F5D4]/20"
            style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
          >
            <Bot className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-[#94A3B8]">
            GradePilot
          </span>
        </Link>

        {/* Card */}
        <div className="p-8 rounded-3xl border border-white/5 bg-[#141B3A]/80 backdrop-blur-xl shadow-[0_20px_60px_rgba(0,0,0,0.5)]">
          {/* Tab switcher */}
          <div className="flex rounded-xl bg-black/30 p-1 mb-8">
            {(['signin', 'signup'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(null); setMessage(null); }}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all ${
                  mode === m
                    ? 'bg-white/10 text-white shadow'
                    : 'text-[#94A3B8] hover:text-white'
                }`}
              >
                {m === 'signin' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            <motion.form
              key={mode}
              initial={{ opacity: 0, x: mode === 'signup' ? 20 : -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: mode === 'signup' ? -20 : 20 }}
              transition={{ duration: 0.2 }}
              onSubmit={handleSubmit}
              className="flex flex-col gap-4"
            >
              {mode === 'signup' && (
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                  <input
                    type="text"
                    placeholder="Full name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all placeholder:text-[#94A3B8]"
                  />
                </div>
              )}

              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type="email"
                  placeholder="Email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all placeholder:text-[#94A3B8]"
                />
              </div>

              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all placeholder:text-[#94A3B8]"
                />
              </div>

              {error && (
                <p className="text-sm text-[#FF4D6D] bg-[#FF4D6D]/10 border border-[#FF4D6D]/20 rounded-xl px-4 py-2.5">
                  {error}
                </p>
              )}
              {message && (
                <p className="text-sm text-[#00F5D4] bg-[#00F5D4]/10 border border-[#00F5D4]/20 rounded-xl px-4 py-2.5">
                  {message}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="flex items-center justify-center gap-2 w-full py-3.5 rounded-xl text-sm font-bold text-[#0B0F2A] mt-2 disabled:opacity-60 disabled:cursor-not-allowed transition-all hover:scale-[1.02] active:scale-[0.98] shadow-[0_4px_20px_rgba(109,74,255,0.3)]"
                style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    {mode === 'signin' ? 'Sign In' : 'Create Account'}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </motion.form>
          </AnimatePresence>
        </div>

        <p className="text-center text-xs text-[#94A3B8] mt-6">
          By continuing you agree to our{' '}
          <span className="text-[#00F5D4] cursor-pointer hover:underline">Terms of Service</span>
        </p>
      </motion.div>
    </div>
  );
}
