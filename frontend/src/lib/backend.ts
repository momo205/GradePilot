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

type ErrorBody = { detail?: unknown } | null;

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
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
        Authorization: `Bearer ${token}`,
      },
    });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    throw new BackendError(`Network error: ${msg}. Is the backend running?`, 0, null);
  }

  const contentType = res.headers.get('content-type') ?? '';
  const body = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);

  if (!res.ok) {
    const message =
      (body &&
        typeof body === 'object' &&
        'detail' in body &&
        String((body as ErrorBody)?.detail ?? '')) ||
      `Request failed (${res.status})`;
    throw new BackendError(String(message), res.status, body);
  }

  return body as T;
}

export type ClassOut = {
  id: string;
  user_id: string;
  title: string;
  semester_start?: string | null;
  semester_end?: string | null;
  timezone?: string | null;
  availability_json?: Record<string, unknown> | null;
  created_at: string;
};

export type ClassSummaryOut = {
  clazz: ClassOut;
  deadline_count: number;
  next_deadline_id: string | null;
  next_deadline_title: string | null;
  next_deadline_due_at: string | null;
  latest_study_plan_id: string | null;
  latest_study_plan_created_at: string | null;
};

export type NotesOut = {
  id: string;
  class_id: string;
  user_id: string;
  notes_text: string;
  created_at: string;
};

export type DeadlineOut = {
  id: string;
  class_id: string;
  user_id: string;
  title: string;
  due_text: string;
  due_at: string | null;
  completed_at?: string | null;
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

export type PracticeQuestion = { q: string; a: string };

export function generatePractice(classId: string, topic: string, count: number, difficulty: string) {
  return backendFetch<{ questions: PracticeQuestion[] }>(`/classes/${classId}/practice`, {
    method: 'POST',
    body: JSON.stringify({ topic, count, difficulty }),
  });
}

export function listClasses() {
  return backendFetch<ClassOut[]>('/classes');
}

export function createClass(title: string) {
  return backendFetch<ClassOut>('/classes', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export function getClassSummary(classId: string) {
  return backendFetch<ClassSummaryOut>(`/classes/${classId}`);
}

export function addNotes(classId: string, notes_text: string) {
  return backendFetch<NotesOut>(`/classes/${classId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ notes_text }),
  });
}

export function getClassNotes(classId: string) {
  return backendFetch<NotesOut[]>(`/classes/${classId}/notes`);
}

export function createStudyPlan(classId: string, notesId?: string) {
  return backendFetch<StudyPlanOut>(`/classes/${classId}/study-plan`, {
    method: 'POST',
    body: JSON.stringify({ notes_id: notesId ?? null }),
  });
}

export function createSemesterStudyPlan(
  classId: string,
  payload: {
    semester_start: string;
    semester_end: string;
    timezone: string;
    availability?: { day: string; start_time: string; end_time: string }[] | null;
  }
) {
  return backendFetch<StudyPlanOut>(`/classes/${classId}/study-plan/semester`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getLatestStudyPlan(classId: string) {
  return backendFetch<StudyPlanOut>(`/classes/${classId}/study-plan/latest`);
}

export function listDeadlines(classId: string) {
  return backendFetch<DeadlineOut[]>(`/classes/${classId}/deadlines`);
}

export function createDeadline(classId: string, title: string, due: string) {
  return backendFetch<DeadlineOut>(`/classes/${classId}/deadlines`, {
    method: 'POST',
    body: JSON.stringify({ title, due }),
  });
}

export function deleteDeadline(classId: string, deadlineId: string) {
  return backendFetch<{ ok: boolean }>(`/classes/${classId}/deadlines/${deadlineId}`, {
    method: 'DELETE',
  });
}

export function updateDeadline(classId: string, deadlineId: string, payload: { completed?: boolean }) {
  return backendFetch<DeadlineOut>(`/classes/${classId}/deadlines/${deadlineId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function importDeadlinesFromSyllabus(classId: string, file: File) {
  return (async () => {
    const token = await getAccessToken();
    const body = new FormData();
    body.append('file', file, file.name);
    const res = await fetch(`${BACKEND_URL}/classes/${classId}/deadlines/import`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body,
    });
    const contentType = res.headers.get('content-type') ?? '';
    const parsed = contentType.includes('application/json')
      ? await res.json().catch(() => null)
      : await res.text().catch(() => null);
    if (!res.ok) {
      const message =
        (parsed &&
          typeof parsed === 'object' &&
          'detail' in parsed &&
          String((parsed as ErrorBody)?.detail ?? '')) ||
        `Request failed (${res.status})`;
      throw new BackendError(String(message), res.status, parsed);
    }
    return parsed as { created: number };
  })();
}

export type SummariseOut = {
  title: string;
  summary: string;
  key_topics: string[];
  important_dates: string[];
  extracted_notes: string;
};

export function summariseDocument(filename: string, raw_text: string) {
  return backendFetch<SummariseOut>('/summarise', {
    method: 'POST',
    body: JSON.stringify({ filename, raw_text }),
  });
}

export type UserSettingsOut = {
  notificationsEnabled: boolean;
  daysBeforeDeadline: number;
  googleConnected: boolean;
  timezone: string | null;
};

export function getUserSettings() {
  return backendFetch<UserSettingsOut>('/settings');
}

export function updateUserSettings(payload: Partial<UserSettingsOut>) {
  return backendFetch<UserSettingsOut>('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export type ExtractPdfOut = {
  filename: string;
  raw_text: string;
};

/** Server-side PDF text extraction (avoids pdf.js in the browser). */
export type MaterialIngestOut = {
  document_id: string;
  chunks_created: number;
};

export type ClassAskSource = {
  document_id: string;
  filename: string;
  document_type: string;
  chunk_index: number;
  snippet: string;
};

export type ClassAskOut = {
  answer: string;
  sources: ClassAskSource[];
};

export type ChatSessionOut = {
  id: string;
  user_id: string;
  status: string;
  created_at: string;
};

export type ChatMessageOut = {
  id: string;
  session_id: string;
  user_id: string;
  role: string;
  content: string;
  created_at: string;
};

export type ChatToolAction = { type: string; payload: Record<string, unknown> };

export type ChatReplyOut = {
  session: ChatSessionOut;
  messages: ChatMessageOut[];
  state: Record<string, unknown>;
  tool_actions: ChatToolAction[];
  complete?: boolean;
  class_id?: string | null;
  next_url?: string | null;
};

export function createOrGetChatSession() {
  return backendFetch<ChatSessionOut>('/chat/sessions', { method: 'POST' });
}

export function getChatSession(sessionId: string) {
  return backendFetch<ChatReplyOut>(`/chat/sessions/${sessionId}`);
}

export function sendChatMessage(sessionId: string, content: string) {
  return backendFetch<ChatReplyOut>(`/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

/** Index a PDF for class-scoped RAG (chunk + embed + store). */
export async function uploadMaterialPdf(
  classId: string,
  file: File,
  documentType: string = 'syllabus'
): Promise<MaterialIngestOut> {
  const token = await getAccessToken();
  const body = new FormData();
  body.append('file', file, file.name);
  body.append('document_type', documentType);
  const res = await fetch(`${BACKEND_URL}/classes/${classId}/materials`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body,
  });
  const contentType = res.headers.get('content-type') ?? '';
  const parsed = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);
  if (!res.ok) {
    const message =
      (parsed &&
        typeof parsed === 'object' &&
        'detail' in parsed &&
        String((parsed as ErrorBody)?.detail ?? '')) ||
      `Request failed (${res.status})`;
    throw new BackendError(String(message), res.status, parsed);
  }
  return parsed as MaterialIngestOut;
}

/** Index raw text for class-scoped RAG. */
export async function uploadMaterialText(
  classId: string,
  rawText: string,
  filename: string,
  documentType: string = 'notes'
): Promise<MaterialIngestOut> {
  const token = await getAccessToken();
  const body = new FormData();
  body.append('raw_text', rawText);
  body.append('filename', filename);
  body.append('document_type', documentType);
  const res = await fetch(`${BACKEND_URL}/classes/${classId}/materials`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body,
  });
  const contentType = res.headers.get('content-type') ?? '';
  const parsed = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);
  if (!res.ok) {
    const message =
      (parsed &&
        typeof parsed === 'object' &&
        'detail' in parsed &&
        String((parsed as ErrorBody)?.detail ?? '')) ||
      `Request failed (${res.status})`;
    throw new BackendError(String(message), res.status, parsed);
  }
  return parsed as MaterialIngestOut;
}

export function askClass(
  classId: string,
  question: string,
  opts?: { top_k?: number; document_type?: string | null }
) {
  return backendFetch<ClassAskOut>(`/classes/${classId}/ask`, {
    method: 'POST',
    body: JSON.stringify({
      question,
      top_k: opts?.top_k ?? 6,
      document_type: opts?.document_type ?? null,
    }),
  });
}

export async function extractPdfText(file: File): Promise<ExtractPdfOut> {
  const token = await getAccessToken();
  const body = new FormData();
  body.append('file', file, file.name);
  const res = await fetch(`${BACKEND_URL}/summarise/extract-pdf`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body,
  });
  const contentType = res.headers.get('content-type') ?? '';
  const parsed = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);
  if (!res.ok) {
    const message =
      (parsed &&
        typeof parsed === 'object' &&
        'detail' in parsed &&
        String((parsed as ErrorBody)?.detail ?? '')) ||
      `Request failed (${res.status})`;
    throw new BackendError(String(message), res.status, parsed);
  }
  return parsed as ExtractPdfOut;
}

