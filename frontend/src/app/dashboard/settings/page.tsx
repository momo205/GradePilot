'use client';

import { useId, useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, Calendar, CheckCircle2, Clock, Link2, Settings as SettingsIcon, XCircle } from 'lucide-react';

const DEADLINE_OPTIONS = [1, 2, 3, 5, 7, 14] as const;
type DeadlineDays = (typeof DEADLINE_OPTIONS)[number];

export default function SettingsPage() {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [daysBeforeDeadline, setDaysBeforeDeadline] = useState<DeadlineDays>(3);
  const [googleConnected, setGoogleConnected] = useState(false);

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
        {/* Notification toggle card */}
        <section className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-[#6D4AFF]/15 border border-[#6D4AFF]/25 flex items-center justify-center shrink-0">
                <Bell className="w-5 h-5 text-[#6D4AFF]" />
              </div>
              <div className="min-w-0">
                <label
                  htmlFor={notifySwitchId}
                  className="text-sm font-bold text-white block cursor-pointer"
                >
                  Notifications
                </label>
                <p className="text-[12px] text-slate-400 mt-0.5">
                  Receive reminders for upcoming deadlines and study sessions
                </p>
              </div>
            </div>
            <button
              id={notifySwitchId}
              type="button"
              role="switch"
              aria-checked={notificationsEnabled}
              onClick={() => setNotificationsEnabled((v) => !v)}
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
        </section>

        {/* Days before deadline dropdown */}
        <section className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
          <div className="flex items-start gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-[#00F5D4]/15 border border-[#00F5D4]/25 flex items-center justify-center shrink-0">
              <Clock className="w-5 h-5 text-[#00F5D4]" />
            </div>
            <div className="min-w-0">
              <label
                htmlFor={deadlineSelectId}
                className="text-sm font-bold text-white block"
              >
                Deadline reminder window
              </label>
              <p className="text-[12px] text-slate-400 mt-0.5">
                How many days before a deadline you want to be alerted
              </p>
            </div>
          </div>
          <select
            id={deadlineSelectId}
            value={daysBeforeDeadline}
            onChange={(e) => setDaysBeforeDeadline(Number(e.target.value) as DeadlineDays)}
            disabled={!notificationsEnabled}
            className="w-full bg-[#0B0F2A] border border-white/10 rounded-xl px-4 py-3 text-sm font-semibold text-white focus:outline-none focus:border-[#00F5D4]/50 focus:ring-1 focus:ring-[#00F5D4]/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {DEADLINE_OPTIONS.map((d) => (
              <option key={d} value={d}>
                {d} {d === 1 ? 'day' : 'days'} before
              </option>
            ))}
          </select>
        </section>

        {/* Google connection status card (mock) */}
        <section className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
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
                <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest"
                  style={{
                    background: googleConnected ? 'rgba(0,245,212,0.10)' : 'rgba(255,77,109,0.10)',
                    color: googleConnected ? '#00F5D4' : '#FF4D6D',
                    border: `1px solid ${googleConnected ? 'rgba(0,245,212,0.30)' : 'rgba(255,77,109,0.30)'}`,
                  }}
                >
                  {googleConnected ? (
                    <>
                      <CheckCircle2 className="w-3 h-3" /> Connected
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3 h-3" /> Not connected
                    </>
                  )}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setGoogleConnected((v) => !v)}
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
        </section>

        {/* Current settings summary */}
        <section className="bg-[#141B3A]/50 backdrop-blur-xl border border-[#00F5D4]/20 rounded-[1.25rem] p-5 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#00F5D4] mb-3">
            Current settings
          </p>
          <ul className="flex flex-col gap-2 text-[13px]">
            <li className="flex items-center justify-between">
              <span className="text-slate-400">Notifications</span>
              <span className="text-white font-semibold">{notificationsEnabled ? 'On' : 'Off'}</span>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-slate-400">Reminder window</span>
              <span className="text-white font-semibold">
                {notificationsEnabled
                  ? `${daysBeforeDeadline} ${daysBeforeDeadline === 1 ? 'day' : 'days'} before deadline`
                  : '—'}
              </span>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-slate-400">Google Calendar</span>
              <span className="text-white font-semibold">
                {googleConnected ? 'Connected' : 'Not connected'}
              </span>
            </li>
          </ul>
        </section>
      </div>
    </motion.div>
  );
}
