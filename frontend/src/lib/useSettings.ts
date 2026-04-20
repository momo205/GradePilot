'use client';

import { useState } from 'react';
import { DEFAULT_SETTINGS, DeadlineDays, UserSettings } from './settingsTypes';

export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);

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
