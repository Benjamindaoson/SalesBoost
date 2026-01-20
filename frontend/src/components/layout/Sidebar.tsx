import { LayoutDashboard, Users, History } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link, useLocation } from "react-router-dom";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function Sidebar() {
  const location = useLocation();
  const pathname = location.pathname;

  const menuItems = [
    {
      icon: LayoutDashboard,
      label: "任务管理",
      path: "/dashboard",
    },
    {
      icon: Users,
      label: "客户预演",
      path: "/persona",
    },
    {
      icon: History,
      label: "历史记录",
      path: "/history",
    },
  ];

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 p-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500 text-white font-bold">
          AI
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">销冠AI系统</h1>
          <p className="text-xs text-gray-500">学员端</p>
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
                  ? "bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-md"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <item.icon className={cn("h-5 w-5", isActive ? "text-white" : "text-gray-500")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer User */}
      <div className="border-t p-4">
        <div className="flex items-center gap-3">
          <Avatar className="h-10 w-10 bg-purple-100 text-purple-600">
            <AvatarFallback>张伟</AvatarFallback>
          </Avatar>
          <div>
            <p className="text-sm font-bold text-gray-900">张伟</p>
            <p className="text-xs text-gray-500">销售顾问</p>
          </div>
        </div>
      </div>
    </div>
  );
}
