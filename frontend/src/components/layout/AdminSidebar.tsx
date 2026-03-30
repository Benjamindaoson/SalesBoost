import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store';
import { 
  BookOpen, 
  LayoutDashboard, 
  CheckSquare, 
  BarChart2, 
  Database,
  LogOut,
  Gauge,
  Target,
  Users,
  Settings,
  Key
} from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

export function AdminSidebar() {
  const { user, signOut } = useAuthStore();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const navItems = [
    { to: '/admin/cockpit', icon: Gauge, label: '总裁驾驶舱' },
    { to: '/admin/analysis', icon: Target, label: '方法论洞察' },
    { to: '/admin/users', icon: Users, label: '团队管理' },
    { to: '/admin/knowledge', icon: Database, label: '知识库' },
    { to: '/admin/dashboard', icon: BookOpen, label: '培训管理' },
    { to: '/admin/settings', icon: Settings, label: '系统设置' },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col z-20">
      {/* Logo Area */}
      <div className="p-6 flex items-center space-x-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-md">
          AI
        </div>
        <div>
          <h1 className="text-base font-bold text-gray-900 leading-tight">SalesBoost</h1>
          <p className="text-xs text-gray-500">总裁驾驶舱</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 group ${
                isActive
                  ? 'bg-gradient-to-r from-purple-50 to-indigo-50 text-indigo-700 shadow-sm'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className={`w-5 h-5 mr-3 ${isActive ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User Profile (Bottom) */}
      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center p-2 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
          <Avatar className="h-9 w-9 border border-gray-200">
            <AvatarImage src={user?.user_metadata?.avatar_url} />
            <AvatarFallback className="bg-purple-100 text-purple-700 font-medium">
              {user?.user_metadata?.full_name?.charAt(0) || user?.email?.charAt(0).toUpperCase() || '管'}
            </AvatarFallback>
          </Avatar>
          <div className="ml-3 flex-1 overflow-hidden">
            <p className="text-sm font-medium text-gray-900 truncate">{user?.user_metadata?.full_name || '管理员'}</p>
            <p className="text-xs text-gray-500 truncate">{user?.email || 'admin@company.com'}</p>
          </div>
          <LogOut
            className="w-4 h-4 text-gray-400 hover:text-red-500 ml-2 cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              handleSignOut();
            }}
          />
        </div>
      </div>
    </aside>
  );
}
