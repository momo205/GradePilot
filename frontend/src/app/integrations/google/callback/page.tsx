import { Suspense } from 'react';
import GoogleCallbackClient from './GoogleCallbackClient';

export default function GoogleOAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-[#0A0B10] text-[#F8FAFC] flex items-center justify-center text-sm text-slate-300">
          Loading…
        </div>
      }
    >
      <GoogleCallbackClient />
    </Suspense>
  );
}
