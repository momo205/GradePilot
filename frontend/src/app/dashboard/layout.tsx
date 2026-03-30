export const metadata = {
  title: 'Dashboard | GradePilot',
  description: 'View your optimized study plan.',
};

import LeftSidebar from "@/components/dashboard/LeftSidebar";
import RightSidebar from "@/components/dashboard/RightSidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen w-full bg-[#0B0B11] p-5 gap-6 font-sans overflow-hidden text-white selection:bg-cyan-400/30 selection:text-white">
      {/* Top ambient glow effects */}
      <div className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/10 blur-[120px] pointer-events-none z-0"></div>
      <div className="fixed top-[-5%] right-[-5%] w-[30%] h-[30%] rounded-full bg-cyan-600/10 blur-[120px] pointer-events-none z-0"></div>

      {/* Left Sidebar Fixed Panel */}
      <div className="h-full flex-shrink-0 relative z-10 w-auto">
        <LeftSidebar />
      </div>
      
      {/* Main scrolling content area */}
      <main className="flex-1 h-full overflow-y-auto rounded-3xl relative z-10 custom-scrollbar pr-2">
        {children}
      </main>

      {/* Right Sidebar Fixed Panel */}
      <div className="h-full flex-shrink-0 relative z-10 w-auto">
        <RightSidebar />
      </div>
    </div>
  );
}
