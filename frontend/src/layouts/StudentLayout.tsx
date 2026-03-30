import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store';
import { 
  LayoutDashboard, 
  Users, 
  Clock, 
  Share2,
  Smartphone,
  Settings,
  Swords,
  Target,
  Zap,
  FileText,
  TrendingUp
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

export default function StudentLayout() {
  const { user, signOut } = useAuthStore();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const handleLogin = () => {
    navigate('/login');
  };

  const handleSwitchToAdmin = () => {
    const userRole = user?.user_metadata?.role || user?.app_metadata?.role;
    if (userRole === 'admin') {
      navigate('/admin/dashboard');
    } else {
      toast({
        title: '权限不足',
        description: '您没有管理员权限，无法切换到管理端',
        variant: 'destructive'
      });
    }
  };

  const handleViewH5 = () => {
    window.open(window.location.href, '_blank', 'width=375,height=667');
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'SalesBoost',
        text: 'AI 销售作战平台 · 从训练到成单',
        url: window.location.href,
      });
    } else {
      toast({
        title: '分享链接',
        description: '链接已复制到剪贴板',
      });
    }
  };

  const navItems = [
    { to: '/student/battle-center', icon: Swords, label: '作战中心' },
    { to: '/student/pipeline', icon: TrendingUp, label: '我的漏斗' },
    { to: '/student/live-assist', icon: Zap, label: '实战辅助' },
    { to: '/student/review', icon: FileText, label: '战后复盘' },
    { to: '/student/training', icon: Target, label: '模拟演练' },
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
            <span className="font-bold text-gray-900 text-lg leading-tight">SalesBoost</span>
            <span className="text-xs text-gray-500 font-medium">AI 销售作战系统</span>
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
                    ? "bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-md shadow-primary/20"
                    : "text-gray-500 hover:bg-gray-50 hover:text-gray-900"
                )
              }
            >
              <item.icon className={cn("w-5 h-5 mr-3")} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-100">
          <div className="flex items-center gap-3 p-2">
            <div className="w-10 h-10 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center font-bold">
              {user?.email?.charAt(0).toUpperCase() || '张'}
            </div>
            <div className="flex flex-col overflow-hidden">
              <span className="font-bold text-gray-900 text-sm truncate">
                {user?.user_metadata?.full_name || '张伟'}
              </span>
              <span className="text-xs text-gray-400 truncate">学员数据</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-8 shadow-sm">
          <div className="text-lg font-medium text-gray-900">
            AI Sales Battle System
          </div>
          
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="sm" 
              className="rounded-full gap-2 border-gray-200 text-gray-600 hover:bg-gray-50"
              onClick={handleSwitchToAdmin}
            >
              切换到管理端
            </Button>

            <Button 
              size="sm" 
              className="rounded-full gap-2 bg-purple-50 text-purple-600 hover:bg-purple-100 border border-purple-100 shadow-none"
              onClick={handleViewH5}
            >
              <Smartphone className="w-4 h-4" />
              查看 H5 版本
            </Button>

            <Button 
              variant="outline" 
              size="sm" 
              className="rounded-full gap-2 border-gray-200 text-gray-600 hover:bg-gray-50"
              onClick={handleShare}
            >
              <Share2 className="w-4 h-4" />
              Share
            </Button>
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
