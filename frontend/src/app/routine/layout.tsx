import Sidebar from "@/components/Sidebar";

export default function RoutineLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col lg:flex-row min-h-screen bg-[#F7F4EF]">
      <Sidebar />
      <div className="flex-1 min-w-0 overflow-y-auto pb-20 lg:pb-0">{children}</div>
    </div>
  );
}
