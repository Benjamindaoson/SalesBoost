import { LayoutDashboard, BookOpen, Users, FileText, Database, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link, useLocation } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function AdminSidebar() {
  const location = useLocation();
  const pathname = location.pathname;

  const menuItems = [
    {
      icon: LayoutDashboard,
      label: "仪表盘",
      path: "/admin/dashboard",
    },
    {
      icon: BookOpen,
      label: "课程管理",
      path: "/admin/courses",
    },
    {
      icon: Users,
      label: "人设管理",
      path: "/admin/personas",
    },
    {
      icon: FileText,
      label: "评估配置",
      path: "/admin/evaluation",
    },
    {
      icon: Activity,
      label: "模型进化",
      path: "/admin/evolution",
    },
    {
      icon: Database,
      label: "知识库",
      path: "/admin/knowledge",
    },
  ];

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-slate-900 text-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 p-6 border-b border-slate-800">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white font-bold">
          AD
        </div>
        <div>
          <h1 className="text-lg font-bold">管理控制台</h1>
          <p className="text-xs text-slate-400">系统配置</p>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 space-y-2 px-4 py-4">
        {menuItems.map((item) => {
          const isActive = pathname.startsWith(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-600 text-white shadow-md"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              )}
            >
              <item.icon className={cn("h-5 w-5", isActive ? "text-white" : "text-slate-400")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer User */}
      <div className="border-t border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <Avatar className="h-10 w-10 bg-blue-900 text-blue-200">
            <AvatarFallback>AD</AvatarFallback>
          </Avatar>
          <div>
            <p className="text-sm font-bold">Administrator</p>
            <p className="text-xs text-slate-500">Super Admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}
