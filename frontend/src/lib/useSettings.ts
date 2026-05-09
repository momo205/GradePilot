'use client';

import { useEffect, useState } from 'react';
import { getUserSettings, updateUserSettings } from '@/lib/backend';
import {
  DEFAULT_SETTINGS,
  DeadlineDays,
  StudyWindow,
  UserSettings,
} from './settingsTypes';

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
          preferredStudyWindows: s.preferredStudyWindows ?? [],
          autoScheduleSessions: s.autoScheduleSessions ?? false,
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
    setAutoScheduleSessions: (v: boolean) =>
      setSettings((s) => {
        void updateUserSettings({ autoScheduleSessions: v });
        return { ...s, autoScheduleSessions: v };
      }),
    setPreferredStudyWindows: (windows: StudyWindow[]) =>
      setSettings((s) => {
        void updateUserSettings({ preferredStudyWindows: windows });
        return { ...s, preferredStudyWindows: windows };
      }),
    /** Local-only; after OAuth completes, refetch with getUserSettings() or reload the page. */
    setGoogleConnected: (v: boolean) =>
      setSettings((s) => ({ ...s, googleConnected: v })),
  };
}
