import { useEffect, useState } from 'react';
import {
  Search,
  Calendar,
  Filter,
  Download,
  Eye,
  RotateCcw,
  Award,
  Clock,
  TrendingUp,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { sessionService } from '@/services/session.service';
import { useAuthStore } from '@/store/auth.store';
import { useToast } from '@/hooks/use-toast';
import { HistoryStats, HistoryRecord } from '@/types/business';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { useNavigate } from 'react-router-dom';

/**
 * Calculate duration between two timestamps
 */
const calculateDuration = (start: string, end: string): string => {
  if (!start || !end) return '0分钟';
  const diff = new Date(end).getTime() - new Date(start).getTime();
  const minutes = Math.floor(diff / 60000);
  return `${minutes}分钟`;
};

/**
 * Calculate statistics from sessions
 */
const calculateStats = (sessions: any[]): HistoryStats => {
  const totalRehearsals = sessions.length;
  const scores = sessions.filter(s => s.final_score !== null).map(s => s.final_score);
  const averageScore = scores.length > 0
    ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length)
    : 0;
  const bestScore = scores.length > 0 ? Math.max(...scores) : 0;

  const totalMinutes = sessions.reduce((sum, s) => {
    if (s.started_at && s.ended_at) {
      const diff = new Date(s.ended_at).getTime() - new Date(s.started_at).getTime();
      return sum + Math.floor(diff / 60000);
    }
    return sum;
  }, 0);

  return {
    totalRehearsals,
    averageScore,
    bestScore,
    totalDurationMinutes: totalMinutes
  };
};

export default function History() {
  const [stats, setStats] = useState<HistoryStats | null>(null);
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        const response = await sessionService.listSessions({
          user_id: user.id,
          status: 'completed',
          page: 1,
          page_size: 100
        });

        const sessions = response.items || [];

        // Transform sessions to history records
        const transformedRecords: HistoryRecord[] = sessions.map(session => ({
          id: session.id,
          dateTime: new Date(session.ended_at || session.started_at).toLocaleString('zh-CN'),
          courseName: `课程 ${session.course_id}`,
          customerName: '客户',
          customerRole: '采购经理',
          category: session.task_type || '对话',
          duration: calculateDuration(session.started_at, session.ended_at),
          score: session.final_score || 0,
          scoreLevel: session.final_score >= 90 ? 'excellent' :
                     session.final_score >= 80 ? 'good' :
                     session.final_score >= 70 ? 'average' : 'poor'
        }));

        setRecords(transformedRecords);
        setStats(calculateStats(sessions));
      } catch (error) {
        console.error('Failed to fetch history', error);
        toast({
          variant: "destructive",
          title: "加载失败",
          description: "无法加载历史记录，请刷新页面重试。"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, toast]);

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-50 border-green-100';
    if (score >= 80) return 'text-blue-600 bg-blue-50 border-blue-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-50 border-yellow-100';
    return 'text-red-600 bg-red-50 border-red-100';
  };

  if (loading) {
    return <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 rounded-xl" />)}
      </div>
      <Skeleton className="h-96 rounded-xl" />
    </div>;
  }

  // Empty State Logic
  if (!loading && records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-6">
        <div className="w-24 h-24 rounded-full bg-gray-50 flex items-center justify-center">
          <Clock className="w-10 h-10 text-gray-300" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">暂无历史记录</h2>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            您还没有进行过任何客户预演。开始您的第一次练习，记录将会显示在这里。
          </p>
        </div>
        <Button 
          onClick={() => navigate('/student/customers')}
          className="bg-purple-600 hover:bg-purple-700 text-white rounded-full px-8 py-6 text-lg shadow-lg shadow-purple-200"
        >
          去预演
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">历史记录</h1>
        <p className="text-gray-500 mt-1">查看所有陪练记录</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 mb-1">总陪练次数</p>
            <div className="text-3xl font-bold text-gray-900">{stats?.totalRehearsals}</div>
            <p className="text-xs text-gray-400 mt-1">累计陪练记录</p>
          </div>
          <div className="w-12 h-12 rounded-full bg-purple-50 flex items-center justify-center text-purple-600">
            <RotateCcw className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 mb-1">平均分数</p>
            <div className="text-3xl font-bold text-gray-900">{stats?.averageScore}</div>
            <p className="text-xs text-blue-500 mt-1 font-medium">保持进步</p>
          </div>
          <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center text-blue-600">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 mb-1">最高分数</p>
            <div className="text-3xl font-bold text-gray-900">{stats?.bestScore}</div>
            <p className="text-xs text-green-500 mt-1 font-medium">优秀表现</p>
          </div>
          <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center text-green-600">
            <Award className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 mb-1">总练习时长</p>
            <div className="text-3xl font-bold text-gray-900">{stats?.totalDurationMinutes}</div>
            <p className="text-xs text-gray-400 mt-1">分钟</p>
          </div>
          <div className="w-12 h-12 rounded-full bg-orange-50 flex items-center justify-center text-orange-600">
            <Clock className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input 
            placeholder="搜索课程名称、客户名称、类别..." 
            className="pl-9 bg-gray-50 border-gray-200 focus:bg-white transition-all rounded-full"
          />
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <Button variant="outline" className="rounded-full border-gray-200 text-gray-600 gap-2 flex-1 md:flex-none">
            <Calendar className="w-4 h-4" />
            全部时间
          </Button>
          <Button variant="outline" className="rounded-full border-gray-200 text-gray-600 gap-2 flex-1 md:flex-none">
            <Filter className="w-4 h-4" />
            全部分数
          </Button>
          <Button variant="outline" className="rounded-full border-gray-200 text-gray-600 gap-2 flex-1 md:flex-none">
            <Download className="w-4 h-4" />
            导出
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50/50 border-b border-gray-100">
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">日期时间</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">课程信息</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">客户角色</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">类别</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">时长</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">得分</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {records.map((record) => (
                <tr key={record.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-500">
                      <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                      {record.dateTime.split(' ')[0]}
                      <span className="ml-2 text-xs text-gray-400">{record.dateTime.split(' ')[1]}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{record.courseName}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{record.customerName}</div>
                      <div className="text-xs text-gray-500">{record.customerRole}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
                      {record.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-500">
                      <Clock className="w-4 h-4 mr-2 text-gray-400" />
                      {record.duration}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className={cn("inline-flex items-center justify-center w-10 h-10 rounded-lg border text-sm font-bold", getScoreColor(record.score))}>
                      {record.score}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="sm" className="h-8 rounded-full text-gray-500 hover:text-gray-900 hover:bg-white border border-transparent hover:border-gray-200">
                        <Eye className="w-4 h-4 mr-1.5" />
                        查看详情
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-gray-400 hover:text-gray-900">
                        <RotateCcw className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
