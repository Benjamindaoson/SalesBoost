import { Outlet, useNavigate } from "react-router-dom";
import { AdminSidebar } from "./AdminSidebar";
import { Button } from "@/components/ui/button";

export default function AdminLayout() {
  const navigate = useNavigate();

  return (
    <div className="flex h-screen w-full bg-slate-50 text-slate-900 font-sans">
      <AdminSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header Area (Global Actions) - Simplified, pages handle their own titles */}
        <header className="flex items-center justify-end p-4 bg-white border-b border-slate-200 h-16 px-8">
             <div className="flex items-center gap-3">
                 <Button 
                   variant="outline" 
                   className="rounded-full bg-white text-gray-600 hover:bg-gray-50 border-gray-300 gap-2"
                   onClick={() => navigate('/dashboard')}
                 >
                   <span>↩</span> 返回学员端
                 </Button>
             </div>
        </header>
        
        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-8">
            <Outlet />
        </div>
      </main>
    </div>
  );
}
