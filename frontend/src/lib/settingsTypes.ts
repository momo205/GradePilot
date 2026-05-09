export const DEADLINE_OPTIONS = [1, 2, 3, 5, 7, 14] as const;
export type DeadlineDays = (typeof DEADLINE_OPTIONS)[number];

export type StudyWindow = { start: string; end: string };

export type UserSettings = {
  notificationsEnabled: boolean;
  daysBeforeDeadline: DeadlineDays;
  googleConnected: boolean;
  preferredStudyWindows: StudyWindow[];
  autoScheduleSessions: boolean;
};

export const DEFAULT_SETTINGS: UserSettings = {
  notificationsEnabled: true,
  daysBeforeDeadline: 3,
  googleConnected: false,
  preferredStudyWindows: [],
  autoScheduleSessions: false,
};

export const MAX_STUDY_WINDOWS = 4;
export const HHMM_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

export function isDeadlineDays(value: number): value is DeadlineDays {
  return (DEADLINE_OPTIONS as readonly number[]).includes(value);
}

export function isValidStudyWindow(w: StudyWindow): boolean {
  if (!HHMM_RE.test(w.start) || !HHMM_RE.test(w.end)) return false;
  const [sh, sm] = w.start.split(':').map(Number);
  const [eh, em] = w.end.split(':').map(Number);
  return sh * 60 + sm < eh * 60 + em;
}
