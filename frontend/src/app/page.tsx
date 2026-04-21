import Link from 'next/link';

export default function LandingPage() {
  return (
    <div
      className={[
        'gp-page relative overflow-hidden',
        // subtle dot grid
        '[background-image:radial-gradient(rgba(255,255,255,0.06)_1px,transparent_1px)]',
        '[background-size:22px_22px]',
      ].join(' ')}
    >
      {/* subtle blue glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-80 [background-image:radial-gradient(800px_420px_at_50%_140px,rgba(59,130,246,0.14),transparent_70%)]"
      />

      {/* top nav */}
      <div className="sticky top-0 z-50 border-b border-[#1e1e1e] bg-background/70 backdrop-blur">
        <nav className="gp-container flex h-16 items-center justify-between gap-6">
          <Link href="/" className="text-sm font-medium tracking-tight text-text">
            GradePilot
          </Link>

          <div className="hidden md:flex items-center gap-6">
            <a className="text-sm text-muted hover:text-text transition-colors" href="#features">
              Features
            </a>
            <a className="text-sm text-muted hover:text-text transition-colors" href="#how">
              How it Works
            </a>
            <a className="text-sm text-muted hover:text-text transition-colors" href="#pricing">
              Pricing
            </a>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/auth" className="gp-btn-ghost">
              Sign In
            </Link>
            <Link href="/auth" className="gp-btn">
              Get Started
            </Link>
          </div>
        </nav>
      </div>

      {/* hero */}
      <header className="gp-container pt-16 md:pt-24 pb-14 md:pb-20">
        <div className="mx-auto max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-[11px] font-medium tracking-[0.18em] text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            AI-POWERED ACADEMIC PLANNING
          </div>

          <h1 className="mt-6 text-4xl md:text-5xl font-semibold tracking-tight text-text">
            Your semester, on autopilot.
          </h1>

          <p className="mt-4 text-base md:text-lg text-muted">
            GradePilot turns syllabi and notes into deadlines, practice questions, and a focused game plan.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/auth" className="gp-btn px-5 py-2.5">
              Get Started <span aria-hidden="true">→</span>
            </Link>
            <a href="#how" className="gp-btn-ghost px-5 py-2.5">
              See How It Works
            </a>
          </div>

          <div className="mt-8 flex items-center justify-center gap-2 text-sm text-muted">
            <span className="text-accent" aria-hidden="true">
              ★★★★★
            </span>
            <span>Built for students who want clarity, not chaos.</span>
          </div>
        </div>
      </header>

      {/* features */}
      <section id="features" className="gp-container pb-16 md:pb-24">
        <div className="mx-auto max-w-4xl">
          <div className="flex items-end justify-between gap-6">
            <div>
              <h2 className="text-xl md:text-2xl font-semibold tracking-tight text-text">
                Everything you need to run your week.
              </h2>
              <p className="mt-2 text-sm md:text-base text-muted">
                A single workspace for classes, notes, deadlines, and practice—designed to feel calm.
              </p>
            </div>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                icon: '📄',
                title: 'Syllabus Parsing',
                desc: 'Upload your syllabus, we extract every deadline automatically.',
              },
              {
                icon: '🧠',
                title: 'Practice Questions',
                desc: 'Generate quizzes from your notes in one click.',
              },
              {
                icon: '📅',
                title: 'Smart Deadlines',
                desc: 'Set and track due dates across all your classes.',
              },
              {
                icon: '📂',
                title: 'Class Workspace',
                desc: 'All your notes and materials, organized by course.',
              },
            ].map((f) => (
              <div key={f.title} className="gp-card p-4">
                <div className="flex items-center justify-between">
                  <div className="text-xl">{f.icon}</div>
                  <div
                    aria-hidden="true"
                    className="h-8 w-8 rounded-lg border border-border bg-background/40"
                  />
                </div>
                <div className="mt-4 text-sm font-semibold text-text">{f.title}</div>
                <div className="mt-2 text-sm text-muted leading-relaxed">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* how it works */}
      <section id="how" className="gp-container pb-16 md:pb-24">
        <div className="mx-auto max-w-4xl gp-card p-6 md:p-8">
          <div className="flex items-start justify-between gap-6 flex-col md:flex-row">
            <div>
              <h2 className="text-xl md:text-2xl font-semibold tracking-tight text-text">
                How it works
              </h2>
              <p className="mt-2 text-sm md:text-base text-muted">
                A simple flow that keeps you moving from upload to execution.
              </p>
            </div>
            <a href="/auth" className="gp-btn-ghost">
              Try it now
            </a>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { n: '1', title: 'Upload your syllabus or notes' },
              { n: '2', title: 'GradePilot plans your semester' },
              { n: '3', title: 'Study smarter, not harder' },
            ].map((s, idx) => (
              <div key={s.n} className="relative gp-card p-4 bg-background/40">
                {idx < 2 ? (
                  <div
                    aria-hidden="true"
                    className="hidden md:block absolute top-1/2 -right-2 w-4 h-px bg-border"
                  />
                ) : null}
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center text-sm font-semibold text-text">
                    {s.n}
                  </div>
                  <div className="text-sm font-semibold text-text">{s.title}</div>
                </div>
                <div className="mt-3 text-sm text-muted">
                  {s.n === '1'
                    ? 'Drop in a file or paste text—GradePilot handles the structure.'
                    : s.n === '2'
                      ? 'Deadlines, topics, and study blocks—organized into a plan you can follow.'
                      : 'Generate practice, track due dates, and stay ahead with less stress.'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* pricing (placeholder section for complete nav) */}
      <section id="pricing" className="gp-container pb-16 md:pb-24">
        <div className="mx-auto max-w-4xl">
          <div className="gp-card p-6 md:p-8">
            <h2 className="text-xl md:text-2xl font-semibold tracking-tight text-text">Pricing</h2>
            <p className="mt-2 text-sm md:text-base text-muted">
              Simple, student-friendly pricing. Coming soon.
            </p>
            <div className="mt-6 flex items-center gap-3">
              <Link href="/auth" className="gp-btn">
                Get Started
              </Link>
              <a href="#features" className="gp-btn-ghost">
                Explore Features
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* footer */}
      <footer className="border-t border-border">
        <div className="gp-container py-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <div className="text-sm font-medium tracking-tight text-text">GradePilot</div>
            <div className="mt-2 text-xs text-muted">
              © {new Date().getFullYear()} GradePilot. All rights reserved.
            </div>
          </div>

          <div className="flex items-center gap-5">
            <a className="text-sm text-muted hover:text-text transition-colors" href="#">
              Privacy
            </a>
            <a className="text-sm text-muted hover:text-text transition-colors" href="#">
              Terms
            </a>
            <a className="text-sm text-muted hover:text-text transition-colors" href="#">
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
