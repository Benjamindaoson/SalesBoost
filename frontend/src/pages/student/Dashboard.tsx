import { useEffect, useState } from 'react';
import { taskService, Task as APITask } from '@/services/task.service';
import { sessionService } from '@/services/session.service';
import { useAuthStore } from '@/store/auth.store';
import { useToast } from '@/hooks/use-toast';
import { Task, Statistics } from '@/types/dashboard';
import { StatCard } from '@/components/dashboard/StatCard';
import { TaskTable } from '@/components/dashboard/TaskTable';
import { FilterBar } from '@/components/dashboard/FilterBar';
import { Layers, PlayCircle, CheckCircle, Award, Lock } from 'lucide-react';

/**
 * Calculate statistics from session data
 *
 * @param sessions - Array of training sessions
 * @returns Statistics object
 */
const calculateStatistics = (sessions: any[]): Statistics => {
  const totalTasks = sessions.length;
  const inProgress = sessions.filter(s => s.status === 'active').length;
  const completed = sessions.filter(s => s.status === 'completed').length;

  const scores = sessions
    .filter(s => s.final_score !== null && s.final_score !== undefined)
    .map(s => s.final_score);

  const averageScore = scores.length > 0
    ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length)
    : 0;

  return {
    totalTasks,
    inProgress,
    completed,
    averageScore,
    lockedItems: 0
  };
};

/**
 * Transform API task to dashboard task format
 */
const transformTask = (apiTask: APITask): Task => {
  return {
    id: apiTask.id.toString(),
    courseName: `Task ${apiTask.id}`,
    courseSubtitle: apiTask.description || '',
    taskInfo: apiTask.title,
    taskTag: apiTask.task_type,
    status: apiTask.status as any,
    timeRange: {
      start: apiTask.created_at,
      end: apiTask.updated_at
    },
    progress: {
      completed: apiTask.completion_rate || 0,
      total: 100,
      bestScore: apiTask.average_score || 0
    }
  };
};

export default function StudentDashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<Statistics | null>(null);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const { toast } = useToast();

  useEffect(() => {
    const fetchData = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        // Fetch tasks and sessions in parallel
        const [tasksResponse, sessionsResponse] = await Promise.all([
          taskService.listTasks({ page: 1, page_size: 100 }),
          sessionService.listSessions({
            user_id: user.id,
            page: 1,
            page_size: 1000
          }).catch(() => ({ items: [], total: 0, page: 1, page_size: 1000 }))
        ]);

        // Transform tasks to dashboard format
        const transformedTasks = tasksResponse.items.map(transformTask);
        setTasks(transformedTasks);

        // Calculate statistics from sessions
        const calculatedStats = calculateStatistics(sessionsResponse.items || []);
        setStats(calculatedStats);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
        toast({
          variant: "destructive",
          title: "加载失败",
          description: "无法加载仪表盘数据，请刷新页面重试。"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, toast]);

  const filteredTasks = tasks.filter(task => {
    const matchesFilter = filter === 'all' || task.status === filter;
    const matchesSearch = 
      task.courseName.toLowerCase().includes(searchQuery.toLowerCase()) || 
      task.taskInfo.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">任务管理</h1>
        <p className="text-gray-500 text-sm mt-1">查看所有学习任务</p>
      </div>

      {/* Stat Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard 
            title="全部任务" 
            value={stats.totalTasks} 
            subtitle="任务总数" 
            icon={Layers}
            iconColor="text-purple-600"
            iconBgColor="bg-purple-100"
          />
          <StatCard 
            title="进行中" 
            value={stats.inProgress} 
            subtitle="课程进行中" 
            icon={PlayCircle}
            iconColor="text-blue-500"
            iconBgColor="bg-blue-100"
          />
          <StatCard 
            title="已完成" 
            value={stats.completed} 
            subtitle="课程完成" 
            icon={CheckCircle}
            iconColor="text-green-500"
            iconBgColor="bg-green-100"
          />
          <StatCard 
            title="平均分数" 
            value={stats.averageScore} 
            subtitle="最近成绩" 
            icon={Award}
            iconColor="text-yellow-500"
            iconBgColor="bg-yellow-100"
          />
          <div className="hidden lg:block">
            <StatCard 
               title="锁定"
               value={stats.lockedItems || 0}
               subtitle="待解锁"
               icon={Lock}
               iconColor="text-gray-400"
               iconBgColor="bg-gray-100"
               className="h-full flex items-center justify-center"
            />
          </div>
        </div>
      )}

      {/* Filter and Table */}
      <div className="space-y-4">
        <FilterBar 
          currentFilter={filter} 
          onFilterChange={setFilter}
          onSearch={setSearchQuery}
        />
        <TaskTable tasks={filteredTasks} />
      </div>
    </div>
  );
}
