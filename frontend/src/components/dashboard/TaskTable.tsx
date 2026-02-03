import { Task } from '@/types/dashboard';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Play, Edit2, Trash2, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TaskTableProps {
  tasks: Task[];
}

export function TaskTable({ tasks }: TaskTableProps) {
  const getStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'in-progress':
        return "bg-blue-100 text-blue-700 hover:bg-blue-100/80";
      case 'completed':
        return "bg-green-100 text-green-700 hover:bg-green-100/80";
      case 'pending':
        return "bg-gray-100 text-gray-700 hover:bg-gray-100/80";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getStatusLabel = (status: Task['status']) => {
    switch (status) {
      case 'in-progress': return '进行中';
      case 'completed': return '已结束'; // As per image '已结束' is green
      case 'pending': return '未开始';
      default: return status;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      <Table>
        <TableHeader className="bg-gray-50/50">
          <TableRow>
            <TableHead className="w-[250px]">课程名称</TableHead>
            <TableHead className="w-[200px]">任务信息</TableHead>
            <TableHead>状态</TableHead>
            <TableHead className="w-[200px]">时间范围</TableHead>
            <TableHead className="w-[200px]">进度</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => (
            <TableRow key={task.id} className="hover:bg-muted/50">
              <TableCell className="font-medium">
                <div className="flex flex-col gap-1">
                  <span className="text-base font-semibold text-gray-900">{task.courseName}</span>
                  {task.courseSubtitle && (
                    <span className="text-xs text-gray-500">{task.courseSubtitle}</span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  <span className="text-sm text-gray-700">{task.taskInfo}</span>
                  <div className="flex">
                     <Badge variant="secondary" className={cn("text-xs font-normal", 
                        task.taskTag === '新人培训' || task.taskTag === '必修' ? "bg-purple-100 text-purple-700" : 
                        task.taskTag === '已上线' ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                     )}>
                        {task.taskTag}
                     </Badge>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge className={cn("rounded-full font-normal shadow-none", getStatusColor(task.status))}>
                  {getStatusLabel(task.status)}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="text-sm text-gray-500 flex flex-col">
                  <span>{task.timeRange.start}</span>
                  <span className="text-xs">至 {task.timeRange.end}</span>
                </div>
              </TableCell>
              <TableCell>
                <div className="space-y-1.5 w-full max-w-[140px]">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">完成度</span>
                    <span className="text-purple-600 font-medium">{task.progress.completed}/{task.progress.total}</span>
                  </div>
                  <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary rounded-full transition-all duration-300" 
                      style={{ width: `${(task.progress.completed / task.progress.total) * 100}%` }}
                    />
                  </div>
                  {task.progress.bestScore && (
                    <div className="text-xs text-gray-400">
                      最佳得分: <span className="text-purple-600">{task.progress.bestScore}分</span>
                    </div>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <Button size="sm" className="bg-primary hover:bg-primary/90 text-white gap-1 rounded-full px-4">
                    <Play className="w-3 h-3" /> 去练习
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-gray-600">
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-gray-600">
                    <MessageSquare className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
