'use client';

import { useState } from 'react';

export const DEADLINE_OPTIONS = [1, 2, 3, 5, 7, 14] as const;
export type DeadlineDays = (typeof DEADLINE_OPTIONS)[number];

export type UserSettings = {
  notificationsEnabled: boolean;
  daysBeforeDeadline: DeadlineDays;
  googleConnected: boolean;
};

const DEFAULTS: UserSettings = {
  notificationsEnabled: true,
  daysBeforeDeadline: 3,
  googleConnected: false,
};

export function isDeadlineDays(value: number): value is DeadlineDays {
  return (DEADLINE_OPTIONS as readonly number[]).includes(value);
}

export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULTS);

  return {
    settings,
    setNotificationsEnabled: (v: boolean) =>
      setSettings((s) => ({ ...s, notificationsEnabled: v })),
    setDaysBeforeDeadline: (v: DeadlineDays) =>
      setSettings((s) => ({ ...s, daysBeforeDeadline: v })),
    setGoogleConnected: (v: boolean) =>
      setSettings((s) => ({ ...s, googleConnected: v })),
  };
}
