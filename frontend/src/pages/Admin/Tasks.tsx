import { useState, useEffect } from 'react';
import { 
  Plus, 
  Search, 
  Link as LinkIcon, 
  Copy, 
  Trash2,
  MoreHorizontal
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { taskService, TaskCreate } from '@/services/task.service';
import { Task } from '@/types/dashboard';
import TaskDialog from '@/components/admin/TaskDialog';
import { useToast } from '@/hooks/use-toast';

export default function AdminTasks() {
  const [searchTerm, setSearchTerm] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const { toast } = useToast();

  const fetchTasks = async () => {
    try {
      const data = await taskService.getTasks();
      setTasks(data);
    } catch (error) {
      console.error("Failed to fetch tasks", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleCreateTask = async (data: TaskCreate) => {
    setCreating(true);
    try {
      await taskService.createTask(data);
      toast({
        title: "创建成功",
        description: "新任务已成功创建",
      });
      setCreateDialogOpen(false);
      fetchTasks();
    } catch (error) {
      toast({
        title: "创建失败",
        description: "无法创建任务，请稍后重试",
        variant: "destructive",
      });
    } finally {
      setCreating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_progress':
        return "bg-blue-50 text-blue-600 border-blue-200";
      case 'completed':
        return "bg-green-50 text-green-600 border-green-200";
      case 'locked':
        return "bg-gray-100 text-gray-600 border-gray-200";
      default:
        return "bg-purple-50 text-purple-600 border-purple-200";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'in_progress': return '进行中';
      case 'completed': return '已完成';
      case 'locked': return '未解锁';
      case 'unlocked': return '待开始';
      default: return status;
    }
  };

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">任务管理</h1>
        <p className="text-sm text-gray-500 mt-1">分类和管理学员任务</p>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between">
        <div className="relative w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input 
            placeholder="按名称搜索..." 
            className="pl-9 bg-white border-gray-200 rounded-lg"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex items-center space-x-3">
          <Select defaultValue="student">
            <SelectTrigger className="w-[140px] bg-white border-gray-200 rounded-lg">
              <SelectValue placeholder="请选择学员" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="student">请选择学员</SelectItem>
              <SelectItem value="all">全部学员</SelectItem>
            </SelectContent>
          </Select>

          <Select defaultValue="status">
            <SelectTrigger className="w-[140px] bg-white border-gray-200 rounded-lg">
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="status">全部状态</SelectItem>
              <SelectItem value="active">进行中</SelectItem>
              <SelectItem value="pending">待审核</SelectItem>
              <SelectItem value="unassigned">待分配</SelectItem>
              <SelectItem value="completed">已结束</SelectItem>
            </SelectContent>
          </Select>

          <Button 
            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md rounded-lg"
            onClick={() => setCreateDialogOpen(true)}
          >
            <Plus className="w-4 h-4 mr-2" />
            创建任务
          </Button>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-gray-50/50">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[280px] text-gray-500 font-medium">任务名称</TableHead>
              <TableHead className="text-gray-500 font-medium">任务类型</TableHead>
              <TableHead className="text-gray-500 font-medium">任务状态</TableHead>
              <TableHead className="text-gray-500 font-medium">进度/得分</TableHead>
              <TableHead className="text-gray-500 font-medium">时间范围</TableHead>
              <TableHead className="text-right text-gray-500 font-medium">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
                <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-500">加载中...</TableCell>
                </TableRow>
            ) : tasks.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-500">暂无任务</TableCell>
                </TableRow>
            ) : (
                tasks.map((task) => (
              <TableRow key={task.id} className="hover:bg-gray-50/50 border-gray-100">
                <TableCell className="py-4">
                  <div className="flex flex-col">
                    <span className="text-gray-900 font-medium text-sm">{task.courseName}</span>
                    <span className="text-xs text-gray-400 mt-1">
                      {task.courseSubtitle}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="py-4">
                  <Badge variant="secondary" className="font-normal">
                    {task.taskTag}
                  </Badge>
                </TableCell>
                <TableCell className="py-4">
                  <Badge variant="outline" className={`font-normal rounded-md border px-2.5 py-0.5 ${getStatusColor(task.status)}`}>
                    {getStatusLabel(task.status)}
                  </Badge>
                </TableCell>
                <TableCell className="py-4">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">
                            {task.progress.completed}/{task.progress.total}
                        </span>
                        {task.progress.bestScore > 0 && (
                            <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200 text-xs">
                                {task.progress.bestScore}分
                            </Badge>
                        )}
                    </div>
                </TableCell>
                <TableCell className="py-4 text-sm text-gray-500">
                    {task.timeRange.start ? new Date(task.timeRange.start).toLocaleDateString() : '-'} 
                    <span className="mx-1">~</span>
                    {task.timeRange.end ? new Date(task.timeRange.end).toLocaleDateString() : '-'}
                </TableCell>
                <TableCell className="py-4 text-right">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-gray-600">
                      <MoreHorizontal className="w-4 h-4" />
                    </Button>
                </TableCell>
              </TableRow>
            )))}
          </TableBody>
        </Table>
      </div>

      <TaskDialog 
        open={createDialogOpen} 
        onOpenChange={setCreateDialogOpen}
        onSave={handleCreateTask}
        loading={creating}
      />
    </div>
  );
}
