"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, BookOpen, AlertCircle, X, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { getCalendarEvents, syncCalendarEvents } from "@/lib/backend";

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

type ViewType = "month" | "week";

export interface CalendarEvent {
  id: string | number;
  title: string;
  date: Date;
  type: string;
  time: string;
  description: string;
}

const DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOURS_OF_DAY = Array.from({ length: 13 }, (_, i) => i + 8); // 8 AM to 8 PM

export default function CalendarPage() {
  const [view, setView] = useState<ViewType>("month");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    import("@/lib/backend").then(({ checkCalendarConnection }) => {
      checkCalendarConnection()
        .then(res => setIsConnected(res.connected))
        .catch(err => console.error("Could not check calendar status", err));
    });
  }, []);

  const handleSync = async () => {
    try {
      setIsSyncing(true);
      if (!isConnected) {
        const { getCalendarAuthUrl } = await import("@/lib/backend");
        const { url } = await getCalendarAuthUrl();
        window.location.href = url;
      } else {
        await import("@/lib/backend").then(m => m.syncCalendarEvents());
      }
    } catch (err) {
      console.error("Failed to sync calendar", err);
    } finally {
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    getCalendarEvents()
      .then((data) => {
        const mapped = data.map((ev) => {
          const startDate = new Date(ev.start_datetime);
          const timeString = startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          return {
            id: ev.id,
            title: ev.title,
            date: startDate,
            type: ev.type || "study",
            time: timeString,
            description: ev.description || "Study block",
          };
        });
        setEvents(mapped);
      })
      .catch((err) => {
        console.error("Failed to load events", err);
      });
  }, []);

  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth();

  const handlePrev = () => {
    if (view === "month") {
      setCurrentDate(new Date(currentYear, currentMonth - 1, 1));
    } else {
      const newDate = new Date(currentDate);
      newDate.setDate(newDate.getDate() - 7);
      setCurrentDate(newDate);
    }
  };

  const handleNext = () => {
    if (view === "month") {
      setCurrentDate(new Date(currentYear, currentMonth + 1, 1));
    } else {
      const newDate = new Date(currentDate);
      newDate.setDate(newDate.getDate() + 7);
      setCurrentDate(newDate);
    }
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  // --- Month View Helpers ---
  const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const daysInPrevMonth = new Date(currentYear, currentMonth, 0).getDate();
  
  const monthDays = [];
  // Previous month trailing days
  for (let i = 0; i < firstDayOfMonth; i++) {
    monthDays.push({
      day: daysInPrevMonth - firstDayOfMonth + i + 1,
      isCurrentMonth: false,
      date: new Date(currentYear, currentMonth - 1, daysInPrevMonth - firstDayOfMonth + i + 1)
    });
  }
  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    monthDays.push({
      day: i,
      isCurrentMonth: true,
      date: new Date(currentYear, currentMonth, i)
    });
  }
  // Next month leading days (to complete the grid of 42 cells typically)
  const remainingCells = 42 - monthDays.length;
  for (let i = 1; i <= remainingCells; i++) {
    monthDays.push({
      day: i,
      isCurrentMonth: false,
      date: new Date(currentYear, currentMonth + 1, i)
    });
  }

  // --- Week View Helpers ---
  const startOfWeek = new Date(currentDate);
  startOfWeek.setDate(currentDate.getDate() - currentDate.getDay());
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(startOfWeek);
    d.setDate(d.getDate() + i);
    return d;
  });

  const isSameDay = (d1: Date, d2: Date) => 
    d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate();

  const isToday = (d: Date) => isSameDay(d, new Date());

  const getEventsForDate = (date: Date) => {
    return events.filter(e => isSameDay(e.date, date));
  };

  const renderEventBadge = (event: CalendarEvent, compact = false) => {
    const colors = {
      exam: "bg-rose-500/20 text-rose-300 border-rose-500/30",
      assignment: "bg-amber-500/20 text-amber-300 border-amber-500/30",
      study: "bg-[#00F5D4]/20 text-[#00F5D4] border-[#00F5D4]/30"
    };
    const icons = {
      exam: AlertCircle,
      assignment: BookOpen,
      study: Clock
    };
    const Icon = icons[event.type as keyof typeof icons];
    const colorClass = colors[event.type as keyof typeof colors];

    return (
      <button 
        key={event.id}
        onClick={() => setSelectedEvent(event)}
        className={cn("text-left cursor-pointer transition-transform hover:scale-[1.02] flex flex-col gap-0.5 rounded-lg border p-1.5 backdrop-blur-md shadow-sm w-full", colorClass)}
      >
        <div className="flex items-center gap-1.5">
          <Icon className="w-3 h-3 shrink-0" />
          <span className="text-[10px] font-bold leading-none truncate">{event.title}</span>
        </div>
        {!compact && <span className="text-[9px] opacity-70 ml-4">{event.time}</span>}
      </button>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.1, ease: "easeOut" }}
      className="h-full flex flex-col pt-3 pb-8 px-2 max-w-[1200px] mx-auto w-full z-10 relative"
    >
      {/* Header section */}
      <header className="flex flex-col md:flex-row md:items-end justify-between mb-8 pl-2 gap-4">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-2 leading-none flex items-center gap-3">
            <CalendarIcon className="w-8 h-8 text-[#7364d9]" />
            Calendar
          </h1>
          <p className="text-slate-400 text-xs font-semibold tracking-wide">
            Track your study sessions and important deadlines
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Toggle View */}
          <div className="flex items-center p-1 bg-black/40 border border-white/10 rounded-xl backdrop-blur-xl">
            <button
              onClick={() => setView("month")}
              className={cn(
                "px-4 py-1.5 text-xs font-bold rounded-lg transition-all",
                view === "month" ? "bg-[#7364d9]/20 text-[#a78bfa]" : "text-slate-400 hover:text-white"
              )}
            >
              Month
            </button>
            <button
              onClick={() => setView("week")}
              className={cn(
                "px-4 py-1.5 text-xs font-bold rounded-lg transition-all",
                view === "week" ? "bg-[#7364d9]/20 text-[#a78bfa]" : "text-slate-400 hover:text-white"
              )}
            >
              Week
            </button>
          </div>

          <div className="h-6 w-px bg-white/10 mx-2" />

          {/* Navigation */}
          <div className="flex items-center gap-3">
            {/* Sync / Refresh Buttons */}
            <div className="flex items-center gap-2 mr-2">
              <button 
                onClick={handleSync}
                disabled={isSyncing}
                title={isConnected ? "Sync with Google Calendar" : "Connect Google Calendar"}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all border",
                  isSyncing 
                    ? "text-slate-400 bg-white/10 border-white/10 cursor-not-allowed" 
                    : "text-slate-300 bg-white/5 hover:bg-white/10 hover:text-white border-white/5 hover:border-white/10"
                )}
              >
                <RefreshCw className={cn("w-3.5 h-3.5", isSyncing && "animate-spin")} />
                {isSyncing ? (isConnected ? "Syncing..." : "Connecting...") : (isConnected ? "Sync to Google" : "Connect Google")}
              </button>
              <button 
                onClick={handleSync}
                disabled={isSyncing}
                title={isConnected ? "Sync Calendar Data" : "Connect Calendar"}
                className={cn(
                  "p-1.5 rounded-lg flex items-center justify-center relative group transition-all border",
                  isSyncing
                    ? "text-slate-400 bg-white/10 border-white/10 cursor-not-allowed" 
                    : "text-slate-300 bg-white/5 hover:bg-white/10 hover:text-white border-white/5 hover:border-white/10"
                )}
              >
                <svg className={cn("w-4 h-4", isSyncing && "animate-pulse")} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
            
            <div className="h-4 w-px bg-white/10 mx-1" />

            <button onClick={handleToday} className="px-3 py-1.5 text-xs font-bold text-slate-300 hover:text-white bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-all">
              Today
            </button>
            <div className="flex items-center gap-1 bg-black/40 border border-white/10 rounded-xl max-p-1 backdrop-blur-xl">
              <button onClick={handlePrev} className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button onClick={handleNext} className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <h2 className="text-sm font-extrabold text-white min-w-[120px] text-right">
              {view === "month" 
                ? currentDate.toLocaleDateString('default', { month: 'long', year: 'numeric' })
                : `${startOfWeek.toLocaleDateString('default', { month: 'short', day: 'numeric' })} - ${weekDays[6].toLocaleDateString('default', { month: 'short', day: 'numeric', year: 'numeric' })}`
              }
            </h2>
          </div>
        </div>
      </header>

      {/* Calendar Body */}
      <motion.div
        key={view}
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="flex-1 bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] shadow-[0_10px_40px_rgba(0,0,0,0.3)] flex flex-col overflow-hidden relative"
      >
        <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#7364d9]/5 to-transparent pointer-events-none opacity-40 z-0" />
        
        {/* Days of Week Header */}
        <div className="grid grid-cols-7 border-b border-white/10 relative z-10">
          {view === "week" && <div className="w-16 border-r border-white/10 shrink-0" /> /* Time column spacer */}
          <div className={cn("grid grid-cols-7 flex-1", view === "week" && "ml-16 absolute inset-0 left-0 pointer-events-none")}>
             {/* If it's week view, we offset the headers. Let's do it cleanly by handling grid differently for month vs week. */}
          </div>
        </div>

        {view === "month" && (
          <div className="flex-1 flex flex-col relative z-10">
            <div className="grid grid-cols-7 border-b border-white/10 bg-black/20">
              {DAYS_OF_WEEK.map(day => (
                <div key={day} className="py-3 text-center text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  {day}
                </div>
              ))}
            </div>
            <div className="flex-1 grid grid-cols-7 grid-rows-6">
              {monthDays.map((md, i) => {
                const isTdy = isToday(md.date);
                const dayEvents = getEventsForDate(md.date);
                return (
                  <div 
                    key={i} 
                    className={cn(
                      "border-r border-b border-white/5 p-2 flex flex-col gap-1 min-h-[100px] transition-colors hover:bg-white/[0.02]",
                      !md.isCurrentMonth && "opacity-40 bg-black/20",
                      isTdy && "bg-[#7364d9]/[0.03]"
                    )}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className={cn(
                        "text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full",
                        isTdy ? "bg-[#00F5D4] text-black" : "text-slate-300"
                      )}>
                        {md.day}
                      </span>
                      {dayEvents.length > 0 && <span className="text-[10px] text-slate-500 font-bold">{dayEvents.length}</span>}
                    </div>
                    <div className="flex-1 flex flex-col gap-1.5 overflow-y-auto custom-scrollbar pr-1">
                      {dayEvents.map(e => renderEventBadge(e))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {view === "week" && (
          <div className="flex-1 flex flex-col relative z-10 overflow-hidden">
            {/* Week Headers */}
            <div className="flex border-b border-white/10 bg-black/20">
              <div className="w-16 shrink-0 border-r border-white/5" />
              <div className="flex-1 grid grid-cols-7">
                {weekDays.map((wd, i) => {
                  const isTdy = isToday(wd);
                  return (
                    <div key={i} className="py-3 text-center border-r border-white/5 last:border-r-0 flex flex-col items-center gap-1">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{DAYS_OF_WEEK[wd.getDay()]}</span>
                      <span className={cn(
                        "text-sm font-extrabold w-7 h-7 flex items-center justify-center rounded-full",
                         isTdy ? "bg-[#00F5D4] text-black" : "text-white"
                      )}>
                        {wd.getDate()}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Week Grid */}
            <div className="flex-1 flex overflow-y-auto custom-scrollbar">
              <div className="w-16 shrink-0 border-r border-white/5 flex flex-col text-slate-500 text-[10px] font-bold text-right pr-2">
                {HOURS_OF_DAY.map(hour => (
                  <div key={hour} className="h-20 border-b border-transparent relative">
                    <span className="absolute -top-2 right-2">{hour > 12 ? `${hour-12} PM` : `${hour} AM`}</span>
                  </div>
                ))}
              </div>
              <div className="flex-1 grid grid-cols-7 relative">
                {/* Horizontal lines */}
                <div className="absolute inset-0 pointer-events-none flex flex-col">
                   {HOURS_OF_DAY.map(hour => (
                    <div key={hour} className="h-20 border-b border-white/5 w-full" />
                  ))}
                </div>
                {/* Vertical columns and events */}
                 {weekDays.map((wd, i) => {
                  const dayEvents = getEventsForDate(wd);
                  return (
                    <div key={i} className={cn(
                      "border-r border-white/5 last:border-r-0 relative",
                      isToday(wd) && "bg-[#7364d9]/[0.02]"
                    )}>
                      {/* For a pure UI mockup, we'll just stack the events roughly based on time, or simply place them in the column. 
                          Since it's mock and UI only, we can just distribute them. */}
                      <div className="absolute inset-x-1 top-2 flex flex-col gap-2">
                        {dayEvents.map(e => renderEventBadge(e))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

      </motion.div>

      {/* Event Details Side Panel */}
      <AnimatePresence>
        {selectedEvent && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedEvent(null)}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
            />
            <motion.div
              initial={{ x: "100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 bottom-0 w-[400px] bg-[#141B3A]/95 backdrop-blur-3xl border-l border-white/10 z-50 p-6 shadow-2xl flex flex-col"
            >
              <button 
                onClick={() => setSelectedEvent(null)}
                className="absolute top-6 right-6 p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
               >
                 <X className="w-5 h-5" />
              </button>
              
              <div className="mt-8 flex flex-col gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="px-2.5 py-1 rounded-full bg-[#7364d9]/20 text-[#a78bfa] text-[10px] font-bold uppercase tracking-wider border border-[#7364d9]/30">
                      {selectedEvent.type}
                    </span>
                  </div>
                  <h2 className="text-2xl font-extrabold text-white leading-tight">{selectedEvent.title}</h2>
                </div>

                <div className="space-y-4 bg-black/20 rounded-2xl p-5 border border-white/5">
                  <div className="flex items-center gap-3 text-slate-300">
                    <CalendarIcon className="w-5 h-5 text-[#36d3b7]" />
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-0.5">Date</p>
                      <p className="text-sm font-semibold">{selectedEvent.date.toLocaleDateString('default', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</p>
                    </div>
                  </div>
                  <div className="h-px bg-white/5 w-full" />
                  <div className="flex items-center gap-3 text-slate-300">
                    <Clock className="w-5 h-5 text-[#00F5D4]" />
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-0.5">Time</p>
                      <p className="text-sm font-semibold">{selectedEvent.time}</p>
                    </div>
                  </div>
                </div>
                
                <div className="pt-4">
                  <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-3">Description</p>
                  <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {selectedEvent.description}
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
