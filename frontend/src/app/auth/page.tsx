'use client';

import { useState } from 'react';
import { Mail, Lock, User, Loader2 } from 'lucide-react';
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
        router.push('/chat');
        router.refresh();
      }
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen w-full px-6 py-10 flex items-center justify-center bg-[#0B0F2A] text-[#F8FAFC]">
      <div className="w-full max-w-sm">
        <Link href="/" className="block text-sm text-slate-300 hover:text-white transition-colors mb-8">
          ← Back
        </Link>

        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight">GradePilot</h1>
          <p className="mt-2 text-sm text-slate-300">
            Sign in to your focused study workspace.
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="flex gap-2 mb-6">
            {(['signin', 'signup'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError(null);
                  setMessage(null);
                }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                  mode === m
                    ? 'border-white/20 bg-white/10 text-white'
                    : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5'
                }`}
              >
                {m === 'signin' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {mode === 'signup' && (
              <label className="block">
                <span className="text-xs font-medium text-slate-300">Full name</span>
                <div className="mt-2 relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full bg-black/20 border border-white/10 rounded-xl py-2.5 pl-10 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                </div>
              </label>
            )}

            <label className="block">
              <span className="text-xs font-medium text-slate-300">Email</span>
              <div className="mt-2 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-black/20 border border-white/10 rounded-xl py-2.5 pl-10 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                />
              </div>
            </label>

            <label className="block">
              <span className="text-xs font-medium text-slate-300">Password</span>
              <div className="mt-2 relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full bg-black/20 border border-white/10 rounded-xl py-2.5 pl-10 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-white/20"
                />
              </div>
            </label>

            {error && (
              <p className="text-sm text-rose-200 bg-rose-500/10 border border-rose-500/20 rounded-xl px-3 py-2">
                {error}
              </p>
            )}
            {message && (
              <p className="text-sm text-emerald-200 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2">
                {message}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-white text-black px-4 py-2.5 text-sm font-semibold disabled:opacity-60"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {mode === 'signin' ? 'Sign in' : 'Create account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
