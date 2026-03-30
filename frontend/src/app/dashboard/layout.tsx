"use client";

import React from "react";
import LeftSidebar from "@/components/dashboard/LeftSidebar";
import RightSidebar from "@/components/dashboard/RightSidebar";
import { motion } from "framer-motion";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div 
      className="relative min-h-screen w-full text-[#F8FAFC] font-sans selection:bg-[#00F5D4]/30"
      style={{ background: 'radial-gradient(circle at 50% 30%, #141B3A 0%, #0B0F2A 70%)' }}
    >
      {/* Proto decorative background orbs */}
      <div className="absolute top-[20%] left-[10%] w-[30%] h-[30%] bg-[#6D4AFF]/10 rounded-full blur-[120px] mix-blend-screen pointer-events-none" />
      <div className="absolute bottom-[10%] right-[10%] w-[40%] h-[40%] bg-[#00F5D4]/5 rounded-full blur-[150px] mix-blend-screen pointer-events-none" />

      <div className="relative z-10 flex min-h-screen w-full max-w-[1800px] mx-auto p-4 gap-6">
        <motion.div
           initial={{ opacity: 0, x: -50 }}
           animate={{ opacity: 1, x: 0 }}
           transition={{ duration: 0.6, ease: "easeOut" }}
           className="h-full shrink-0 flex"
        >
          <LeftSidebar />
        </motion.div>
        
        <main className="flex-1 min-w-0 relative overflow-y-auto">
          {children}
        </main>
        
        <motion.div
           initial={{ opacity: 0, x: 50 }}
           animate={{ opacity: 1, x: 0 }}
           transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
           className="h-full shrink-0 flex"
        >
          <RightSidebar />
        </motion.div>
      </div>
    </div>
  );
}
