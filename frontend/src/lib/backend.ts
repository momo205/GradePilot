import { createClient } from '@/lib/supabase/client';

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000';

export class BackendError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function getAccessToken(): Promise<string> {
  const supabase = createClient();
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw new Error('Not authenticated');
  }

  let session = data.session ?? null;
  if (!session) {
    throw new Error('Not authenticated');
  }

  // If the token is near expiry (or expired), refresh it before calling backend.
  const expiresAtMs = (session.expires_at ?? 0) * 1000;
  const skewMs = 60_000; // 60s clock skew / network time
  console.debug('[backend] session expires_at', session.expires_at);
  if (expiresAtMs !== 0 && Date.now() + skewMs >= expiresAtMs) {
    console.debug('[backend] refreshing session…');
    const refreshed = await supabase.auth.refreshSession();
    if (refreshed.error || !refreshed.data.session?.access_token) {
      throw new Error('Session expired, please sign in again');
    }
    session = refreshed.data.session;
    console.debug('[backend] refreshed; expires_at', session.expires_at);
  }

  if (!session.access_token) {
    throw new Error('Not authenticated');
  }

  console.debug('[backend] using access token length', session.access_token.length);
  return session.access_token;
}

export async function backendFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const token = await getAccessToken();
  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });

  const contentType = res.headers.get('content-type') ?? '';
  const body = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);

  if (!res.ok) {
    const message =
      (body && typeof body === 'object' && 'detail' in body && (body as any).detail) ||
      `Request failed (${res.status})`;
    throw new BackendError(String(message), res.status, body);
  }

  return body as T;
}

export type ClassOut = {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
};

export type NotesOut = {
  id: string;
  class_id: string;
  user_id: string;
  notes_text: string;
  created_at: string;
};

export type StudyPlanOut = {
  id: string;
  class_id: string;
  user_id: string;
  source_notes_id: string | null;
  plan_json: {
    title: string;
    goals: string[];
    schedule: { day: string; tasks: string[] }[];
  };
  model: string;
  created_at: string;
};

export function createClass(title: string) {
  return backendFetch<ClassOut>('/classes', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export function addNotes(classId: string, notes_text: string) {
  return backendFetch<NotesOut>(`/classes/${classId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ notes_text }),
  });
}

export function createStudyPlan(classId: string, notesId?: string) {
  return backendFetch<StudyPlanOut>(`/classes/${classId}/study-plan`, {
    method: 'POST',
    body: JSON.stringify({ notes_id: notesId ?? null }),
  });
}

