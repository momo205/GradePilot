'use client';

import { useEffect, useState } from 'react';
import { getUserSettings, updateUserSettings } from '@/lib/backend';
import { DEFAULT_SETTINGS, DeadlineDays, UserSettings } from './settingsTypes';

export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await getUserSettings();
        if (cancelled) return;
        setSettings({
          notificationsEnabled: s.notificationsEnabled,
          daysBeforeDeadline: s.daysBeforeDeadline as DeadlineDays,
          googleConnected: s.googleConnected,
        });
      } catch {
        // If settings aren't available yet, keep defaults.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    settings,
    setNotificationsEnabled: (v: boolean) =>
      setSettings((s) => {
        void updateUserSettings({ notificationsEnabled: v });
        return { ...s, notificationsEnabled: v };
      }),
    setDaysBeforeDeadline: (v: DeadlineDays) =>
      setSettings((s) => {
        void updateUserSettings({ daysBeforeDeadline: v });
        return { ...s, daysBeforeDeadline: v };
      }),
    setGoogleConnected: (v: boolean) =>
      setSettings((s) => ({ ...s, googleConnected: v })),
  };
}
