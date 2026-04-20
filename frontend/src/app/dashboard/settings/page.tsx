'use client';

import { ReactNode, useId } from 'react';
import { motion } from 'framer-motion';
import { Bell, Calendar, CheckCircle2, Clock, Link2, Settings as SettingsIcon, XCircle } from 'lucide-react';
import {
  DEADLINE_OPTIONS,
  DeadlineDays,
  isDeadlineDays,
  useSettings,
} from '@/lib/useSettings';

export default function SettingsPage() {
  const {
    settings,
    setNotificationsEnabled,
    setDaysBeforeDeadline,
    setGoogleConnected,
  } = useSettings();
  const { notificationsEnabled, daysBeforeDeadline, googleConnected } = settings;

  const notifySwitchId = useId();
  const deadlineSelectId = useId();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="pt-3 pb-12 px-2 max-w-[1000px] mx-auto w-full h-full flex flex-col"
    >
      <header className="mb-6 pl-2">
        <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-1 leading-none flex items-center gap-3">
          <SettingsIcon className="w-6 h-6 text-[#00F5D4]" />
          Settings
        </h1>
        <p className="text-slate-400 text-xs font-semibold tracking-wide">
          Manage notifications, deadline reminders, and connected accounts
        </p>
      </header>

      <div className="flex flex-col gap-4">
        <SettingsCard>
          <div className="flex items-center justify-between gap-4">
            <SettingRow
              icon={<Bell className="w-5 h-5 text-[#6D4AFF]" />}
              iconBg="bg-[#6D4AFF]/15 border-[#6D4AFF]/25"
              title="Notifications"
              description="Receive reminders for upcoming deadlines and study sessions"
              labelFor={notifySwitchId}
            />
            <button
              id={notifySwitchId}
              type="button"
              role="switch"
              aria-checked={notificationsEnabled}
              onClick={() => setNotificationsEnabled(!notificationsEnabled)}
              className={`relative shrink-0 inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-[#00F5D4]/60 ${
                notificationsEnabled ? 'bg-[#00F5D4]' : 'bg-white/10'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  notificationsEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </SettingsCard>

        <SettingsCard>
          <div className="mb-4">
            <SettingRow
              icon={<Clock className="w-5 h-5 text-[#00F5D4]" />}
              iconBg="bg-[#00F5D4]/15 border-[#00F5D4]/25"
              title="Deadline reminder window"
              description="How many days before a deadline you want to be alerted"
              labelFor={deadlineSelectId}
            />
          </div>
          <select
            id={deadlineSelectId}
            value={daysBeforeDeadline}
            onChange={(e) => {
              const next = Number(e.target.value);
              if (isDeadlineDays(next)) setDaysBeforeDeadline(next);
            }}
            disabled={!notificationsEnabled}
            className="w-full bg-[#0B0F2A] border border-white/10 rounded-xl px-4 py-3 text-sm font-semibold text-white focus:outline-none focus:border-[#00F5D4]/50 focus:ring-1 focus:ring-[#00F5D4]/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {DEADLINE_OPTIONS.map((d) => (
              <option key={d} value={d}>
                {d} {d === 1 ? 'day' : 'days'} before
              </option>
            ))}
          </select>
        </SettingsCard>

        <SettingsCard>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                <Calendar className="w-5 h-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-white">Google Calendar</p>
                <p className="text-[12px] text-slate-400 mt-0.5">
                  Sync deadlines and study blocks with your Google Calendar
                </p>
                <ConnectionBadge connected={googleConnected} />
              </div>
            </div>
            <button
              type="button"
              onClick={() => setGoogleConnected(!googleConnected)}
              className={`shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-[13px] font-bold transition-all focus:outline-none focus:ring-2 focus:ring-[#00F5D4]/60 ${
                googleConnected
                  ? 'bg-white/5 border border-white/10 text-white hover:bg-white/10'
                  : 'bg-gradient-to-r from-[#6D4AFF] to-[#00F5D4] text-black shadow-[0_4px_25px_rgba(0,245,212,0.25)] hover:shadow-[0_4px_30px_rgba(0,245,212,0.45)]'
              }`}
            >
              <Link2 className="w-4 h-4" />
              {googleConnected ? 'Disconnect' : 'Connect Google'}
            </button>
          </div>
        </SettingsCard>

        <SettingsCard accent>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#00F5D4] mb-3">
            Current settings
          </p>
          <ul className="flex flex-col gap-2 text-[13px]">
            <SummaryRow label="Notifications" value={notificationsEnabled ? 'On' : 'Off'} />
            <SummaryRow
              label="Reminder window"
              value={
                notificationsEnabled
                  ? `${daysBeforeDeadline} ${daysBeforeDeadline === 1 ? 'day' : 'days'} before deadline`
                  : '—'
              }
            />
            <SummaryRow label="Google Calendar" value={googleConnected ? 'Connected' : 'Not connected'} />
          </ul>
        </SettingsCard>
      </div>
    </motion.div>
  );
}

function SettingsCard({ children, accent }: { children: ReactNode; accent?: boolean }) {
  return (
    <section
      className={`bg-[#141B3A]/50 backdrop-blur-xl border rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)] ${
        accent ? 'border-[#00F5D4]/20' : 'border-white/5'
      }`}
    >
      {children}
    </section>
  );
}

function SettingRow({
  icon,
  iconBg,
  title,
  description,
  labelFor,
}: {
  icon: ReactNode;
  iconBg: string;
  title: string;
  description: string;
  labelFor: string;
}) {
  return (
    <div className="flex items-start gap-3 min-w-0">
      <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${iconBg}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <label htmlFor={labelFor} className="text-sm font-bold text-white block cursor-pointer">
          {title}
        </label>
        <p className="text-[12px] text-slate-400 mt-0.5">{description}</p>
      </div>
    </div>
  );
}

function ConnectionBadge({ connected }: { connected: boolean }) {
  return (
    <div
      className="mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest"
      style={{
        background: connected ? 'rgba(0,245,212,0.10)' : 'rgba(255,77,109,0.10)',
        color: connected ? '#00F5D4' : '#FF4D6D',
        border: `1px solid ${connected ? 'rgba(0,245,212,0.30)' : 'rgba(255,77,109,0.30)'}`,
      }}
    >
      {connected ? (
        <>
          <CheckCircle2 className="w-3 h-3" /> Connected
        </>
      ) : (
        <>
          <XCircle className="w-3 h-3" /> Not connected
        </>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-center justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="text-white font-semibold">{value}</span>
    </li>
  );
}

export type { DeadlineDays };
