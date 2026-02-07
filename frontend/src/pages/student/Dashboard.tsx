import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/auth.store';
import { useToast } from '@/hooks/use-toast';
import { Task, Statistics } from '@/types/dashboard';
import { StatCard } from '@/components/dashboard/StatCard';
import { TaskTable } from '@/components/dashboard/TaskTable';
import { FilterBar } from '@/components/dashboard/FilterBar';
import { Layers, PlayCircle, CheckCircle, Award, Lock, Trophy } from 'lucide-react';
import { getTasks, getStatistics } from '@/services/task.service';

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
      setLoading(true);
      try {
        // Fetch real data from backend API
        const [tasksData, statsData] = await Promise.all([
          getTasks(),
          getStatistics()
        ]);

        setTasks(tasksData);
        setStats(statsData);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
        toast({
          variant: "destructive",
          title: "加载失败",
          description: "无法连接到后端服务器。请确保后端正在运行 (python main.py)。"
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
