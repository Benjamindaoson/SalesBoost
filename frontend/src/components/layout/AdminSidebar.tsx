import { LayoutDashboard, BookOpen, Users, FileText, Database, UserCog, MessageSquare, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link, useLocation } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function AdminSidebar() {
  const location = useLocation();
  const pathname = location.pathname;

  const menuItems = [
    {
      icon: UserCog,
      label: "账号与权限管理",
      path: "/admin/users",
    },
    {
      icon: Database,
      label: "知识库管理",
      path: "/admin/knowledge",
    },
    {
      icon: BookOpen,
      label: "课程管理",
      path: "/admin/courses",
    },
    {
      icon: FileText,
      label: "评估体系管理",
      path: "/admin/evaluation",
    },
    {
      icon: LayoutDashboard,
      label: "数据看板",
      path: "/admin/dashboard",
    },
    {
      icon: MessageSquare,
      label: "对练规则管理",
      path: "/admin/rules",
    },
  ];

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-white text-slate-600">
      {/* Header */}
      <div className="flex items-center gap-3 p-6 border-b border-slate-100">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 text-white font-bold shadow-md">
          <Layers className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-900">AI销冠训练平台</h1>
          <p className="text-xs text-slate-400">管理员 · Admin</p>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 space-y-2 px-4 py-6">
        {menuItems.map((item) => {
          // Check if the current path starts with the item path (for sub-routes)
          // But dashboard is /admin/dashboard, users is /admin/users. 
          // Special case: /admin/courses should match /admin/courses/personas etc if we had sub-routes.
          const isActive = pathname.startsWith(item.path);
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-200"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <item.icon className={cn("h-5 w-5", isActive ? "text-white" : "text-slate-400")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer User */}
      <div className="p-4 mt-auto">
        <div className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 bg-slate-50">
            <div className="h-10 w-10 rounded-full bg-orange-500 flex items-center justify-center text-white font-bold shadow-sm">
                管
            </div>
          <div className="overflow-hidden">
            <p className="text-sm font-bold text-slate-900 truncate">管理员</p>
            <p className="text-xs text-slate-500 truncate">Admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}
