import { useEffect, useState } from 'react';
import { 
  RotateCw, 
  TrendingUp, 
  Award, 
  Clock, 
  Search, 
  Download,
  Eye,
  MoreHorizontal
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { sessionService } from '@/services/session.service';
import { HistoryRecord, HistoryStats } from '@/types/business';
import { StatCard } from '@/components/dashboard/StatCard';
import { useAuthStore } from '@/store/auth.store';
import { useToast } from '@/hooks/use-toast';

export default function StudentHistory() {
  const [stats, setStats] = useState<HistoryStats | null>(null);
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const { toast } = useToast();

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // 获取用户的会话列表
        const sessionsData = await sessionService.listSessions({
          user_id: user?.id,
          page: 1,
          page_size: 100
        });

        // 转换为历史记录格式
        const historyRecords: HistoryRecord[] = sessionsData.items.map((session: any) => {
          const startTime = new Date(session.started_at);
          const endTime = session.completed_at ? new Date(session.completed_at) : new Date();
          const durationMinutes = Math.round((endTime.getTime() - startTime.getTime()) / 60000);
          const score = session.final_score || 0;
          const scoreLevel: HistoryRecord['scoreLevel'] =
            score >= 90 ? 'excellent' : score >= 70 ? 'good' : score >= 60 ? 'average' : 'poor';

          return {
            id: session.id,
            dateTime: startTime.toLocaleString('zh-CN', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            }),
            courseName: session.course_id || '未知课程',
            customerName: session.persona_id || '未知客户',
            customerRole: '客户',
            category: '新客户培训',
            duration: `${durationMinutes}分钟`,
            score,
            scoreLevel,
          };
        });

        setRecords(historyRecords);

        // 计算统计数据
        const totalRehearsals = historyRecords.length;
        const scores = historyRecords.map(r => r.score).filter(s => s > 0);
        const averageScore = scores.length > 0
          ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
          : 0;
        const bestScore = scores.length > 0 ? Math.max(...scores) : 0;
        const totalDurationMinutes = historyRecords.reduce((total, record) => {
          const minutes = parseInt(record.duration.replace('分钟', ''));
          return total + (isNaN(minutes) ? 0 : minutes);
        }, 0);

        setStats({
          totalRehearsals,
          averageScore,
          bestScore,
          totalDurationMinutes
        });
      } catch (error) {
        console.error('Failed to fetch history:', error);
        toast({
          variant: 'destructive',
          title: '加载失败',
          description: '无法加载历史记录，请稍后重试'
        });
        // 设置空数据
        setRecords([]);
        setStats({
          totalRehearsals: 0,
          averageScore: 0,
          bestScore: 0,
          totalDurationMinutes: 0
        });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [user, toast]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">历史记录</h1>
        <p className="text-sm text-gray-500 mt-1">查看所有练习记录</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="总训练次数" 
            value={stats.totalRehearsals} 
            subtitle="累计训练记录" 
            icon={RotateCw}
            iconColor="text-purple-600"
            iconBgColor="bg-purple-100"
          />
          <StatCard 
            title="平均分数" 
            value={stats.averageScore} 
            subtitle="保持进步" 
            icon={TrendingUp}
            iconColor="text-blue-500"
            iconBgColor="bg-blue-100"
          />
          <StatCard 
            title="最高分数" 
            value={stats.bestScore} 
            subtitle="优秀表现" 
            icon={Award}
            iconColor="text-green-500"
            iconBgColor="bg-green-100"
          />
          <StatCard 
            title="总练习时长" 
            value={stats.totalDurationMinutes} 
            subtitle="分钟" 
            icon={Clock}
            iconColor="text-orange-500"
            iconBgColor="bg-orange-100"
          />
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-2">
        <div className="relative w-full sm:w-[350px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input 
            placeholder="搜索课程名称、客户名称、类别..." 
            className="pl-9 bg-white border-gray-200 rounded-lg"
          />
        </div>
        
        <div className="flex items-center gap-3 w-full sm:w-auto overflow-x-auto">
           <Select>
            <SelectTrigger className="w-[120px] bg-white border-gray-200">
              <SelectValue placeholder="个别时间" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部时间</SelectItem>
            </SelectContent>
          </Select>

          <Select>
            <SelectTrigger className="w-[120px] bg-white border-gray-200">
              <SelectValue placeholder="个别分数" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分数</SelectItem>
            </SelectContent>
          </Select>

          <Button variant="outline" className="gap-2 border-gray-200 text-gray-600">
            <Download className="w-4 h-4" />
            导出
          </Button>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-gray-50/50">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[200px]">日期时间</TableHead>
              <TableHead className="w-[200px]">课程信息</TableHead>
              <TableHead className="w-[200px]">客户角色</TableHead>
              <TableHead>类别</TableHead>
              <TableHead>时长</TableHead>
              <TableHead>得分</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((record) => (
              <TableRow key={record.id} className="hover:bg-gray-50/50 border-gray-100">
                <TableCell className="py-4">
                  <div className="flex items-center gap-2 text-gray-500 text-sm">
                    <Clock className="w-4 h-4 text-gray-300" />
                    <div className="flex flex-col">
                      <span>{record.dateTime.split(' ')[0]}</span>
                      <span className="text-xs text-gray-400">{record.dateTime.split(' ')[1]}</span>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="font-medium text-gray-900 py-4">{record.courseName}</TableCell>
                <TableCell className="py-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900">{record.customerName}</span>
                    <span className="text-xs text-gray-500">{record.customerRole}</span>
                  </div>
                </TableCell>
                <TableCell className="py-4">
                   <Badge variant="secondary" className="bg-purple-50 text-purple-700 hover:bg-purple-100 font-normal border-0">
                     {record.category}
                   </Badge>
                </TableCell>
                <TableCell className="text-gray-500 text-sm py-4">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-gray-300" />
                    {record.duration}
                  </div>
                </TableCell>
                <TableCell className="py-4">
                  <div className={`
                    w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold border
                    ${record.score >= 90 
                      ? 'bg-green-50 text-green-600 border-green-100' 
                      : record.score >= 80 
                        ? 'bg-blue-50 text-blue-600 border-blue-100'
                        : 'bg-orange-50 text-orange-600 border-orange-100'
                    }
                  `}>
                    {record.score}
                  </div>
                </TableCell>
                <TableCell className="text-right py-4">
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" className="text-gray-500 hover:text-gray-900 gap-1 rounded-full px-3">
                      <Eye className="w-4 h-4" /> 查看详情
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-gray-600 rounded-full">
                      <RotateCw className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
