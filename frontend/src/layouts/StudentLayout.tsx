import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store';
import { 
  LayoutDashboard, 
  Users, 
  Clock, 
  Send, 
  User,
  Share2,
  Smartphone,
  RotateCcw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export default function StudentLayout() {
  const { user, signOut } = useAuthStore();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const handleLogin = () => {
    navigate('/login');
  };

  const navItems = [
    { to: '/student/dashboard', icon: LayoutDashboard, label: '任务管理' },
    { to: '/student/customers', icon: Users, label: '客户预演' },
    { to: '/student/history', icon: Clock, label: '历史记录' },
  ];

  const bottomItems = [
    { to: '/student/publish', icon: Send, label: '发布' },
    { to: '/student/profile', icon: User, label: '我的' },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-100 flex flex-col shadow-sm z-10">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-bold shadow-md shadow-primary/30">
            AI
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-gray-900 text-lg leading-tight">销售AI系统</span>
            <span className="text-xs text-gray-500 font-medium">学员侧</span>
          </div>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center px-4 py-3 text-sm font-medium rounded-full transition-all duration-200",
                  isActive
                    ? "bg-primary text-white shadow-md shadow-primary/20"
                    : "text-gray-500 hover:bg-gray-50 hover:text-gray-900"
                )
              }
            >
              <item.icon className={cn("w-5 h-5 mr-3")} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 mt-auto space-y-2">
           {bottomItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center px-4 py-3 text-sm font-medium rounded-full transition-all duration-200",
                  isActive
                    ? "bg-primary text-white"
                    : "text-gray-400 hover:bg-gray-50 hover:text-gray-700"
                )
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.label}
            </NavLink>
          ))}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-8 shadow-sm">
          <div className="text-lg font-medium text-gray-900">
            AI Sales Training Agent
          </div>
          
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="rounded-full gap-2 border-gray-200 text-gray-600 hover:bg-gray-50">
              <Share2 className="w-4 h-4" />
              Share
            </Button>
            
            <Button size="sm" className="rounded-full gap-2 bg-purple-50 text-primary hover:bg-purple-100 border border-purple-100 shadow-none">
              <Smartphone className="w-4 h-4" />
              查看 H5 版本
            </Button>

            {user ? (
              <div className="flex items-center gap-3 ml-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary text-sm font-medium">
                    {user.email?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <span className="text-sm font-medium text-gray-700 hidden md:block">
                    {user.user_metadata?.name || user.email?.split('@')[0] || 'User'}
                  </span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={handleSignOut}
                  className="text-gray-500 hover:text-red-600"
                >
                  退出
                </Button>
              </div>
            ) : (
              <Button 
                onClick={handleLogin}
                className="ml-2 rounded-full bg-primary hover:bg-primary/90 text-white shadow-sm"
              >
                登录 / 注册
              </Button>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
