import { Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store';
import { 
  HelpCircle,
  Share2,
  ChevronDown
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { AdminSidebar } from '@/components/layout/AdminSidebar';

export default function AdminLayout() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSwitchToStudent = () => {
    navigate('/student/dashboard');
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'SalesBoost - 管理端',
        text: 'AI 销售作战平台 · 训练 · 管道 · 实战',
        url: window.location.href,
      });
    } else {
      toast({
        title: '分享链接',
        description: '链接已复制到剪贴板',
      });
    }
  };

  const handleHelp = () => {
    toast({
      title: '帮助中心',
      description: '帮助文档正在编写中，请联系管理员获取支持',
    });
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <AdminSidebar />

      {/* Main Layout */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 z-10">
          <div className="flex items-center">
            <h2 className="text-lg font-semibold text-gray-800">SalesBoost 总裁驾驶舱</h2>
            <ChevronDown className="w-4 h-4 ml-2 text-gray-400 cursor-pointer" />
          </div>
          
          <div className="flex items-center space-x-4">
            <Button 
              variant="ghost" 
              size="icon" 
              className="rounded-full text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              onClick={handleHelp}
            >
              <HelpCircle className="w-5 h-5" />
            </Button>
            
            <Button 
              variant="outline" 
              className="rounded-full border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              onClick={handleSwitchToStudent}
            >
              切换到学员端
            </Button>
            
            <Button 
              className="rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200"
              onClick={handleShare}
            >
              <Share2 className="w-4 h-4 mr-2" />
              Share
            </Button>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto bg-gray-50 p-8">
          <div className="max-w-7xl mx-auto h-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
