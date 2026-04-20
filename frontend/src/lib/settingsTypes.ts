export const DEADLINE_OPTIONS = [1, 2, 3, 5, 7, 14] as const;
export type DeadlineDays = (typeof DEADLINE_OPTIONS)[number];

export type UserSettings = {
  notificationsEnabled: boolean;
  daysBeforeDeadline: DeadlineDays;
  googleConnected: boolean;
};

export const DEFAULT_SETTINGS: UserSettings = {
  notificationsEnabled: true,
  daysBeforeDeadline: 3,
  googleConnected: false,
};

export function isDeadlineDays(value: number): value is DeadlineDays {
  return (DEADLINE_OPTIONS as readonly number[]).includes(value);
}
