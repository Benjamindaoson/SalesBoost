import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Button } from "@/components/ui/button";

export default function Layout() {
  return (
    <div className="flex h-screen w-full bg-gray-50 text-slate-900 font-sans">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header Area (Global Actions) */}
        <header className="flex items-center justify-end p-6 pb-0">
             <div className="flex items-center gap-3">
                 <Button variant="outline" className="rounded-full bg-white text-gray-600 hover:bg-gray-50">
                   切换到管理端
                 </Button>
                 <Button className="rounded-full bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-200">
                   查看 H5 版本
                 </Button>
             </div>
        </header>
        
        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 pt-2">
            <Outlet />
        </div>
      </main>
    </div>
  );
}
