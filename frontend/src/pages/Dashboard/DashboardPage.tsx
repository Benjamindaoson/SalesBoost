import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { taskService } from "@/services/api";
import { StatCard } from "@/components/common/StatCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Filter, Play, Lock, Award, Search, RefreshCw, Eye, MessageSquare, QrCode } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

export default function DashboardPage() {
  const [filterStatus, setFilterStatus] = useState("all");
  const navigate = useNavigate();
  
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['taskStats'],
    queryFn: taskService.getStats
  });

  const { data: tasks, refetch: refetchTasks } = useQuery({
    queryKey: ['tasks', filterStatus],
    queryFn: () => taskService.getTasks({ status: filterStatus })
  });

  const handleRefresh = () => {
    refetchStats();
    refetchTasks();
  };

  const tabs = [
    { id: 'all', label: '全部' },
    { id: 'not_started', label: '未开始' },
    { id: 'in_progress', label: '进行中' },
    { id: 'completed', label: '已结束' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">任务管理</h2>
        <p className="text-gray-500">查看所有学习任务</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard 
          label="全部任务" 
          subLabel="任务总数"
          value={stats?.total || 0} 
          icon={Filter}
          iconClassName="text-purple-600"
          iconBgColor="bg-purple-100"
        />
        <StatCard 
          label="进行中" 
          subLabel="需要完成"
          value={stats?.inProgress || 0} 
          icon={Play}
          iconClassName="text-blue-500"
          iconBgColor="bg-blue-100"
        />
        <StatCard 
          label="已完成" 
          subLabel="恭喜完成"
          value={stats?.completed || 0} 
          icon={Lock}
          iconClassName="text-green-500"
          iconBgColor="bg-green-100"
        />
        <StatCard 
          label="平均分数" 
          subLabel="继续加油"
          value={stats?.averageScore || 0} 
          icon={Award}
          iconClassName="text-orange-500"
          iconBgColor="bg-orange-100"
        />
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white p-2 rounded-lg shadow-sm">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input 
            placeholder="搜索课程名称、任务名称..." 
            className="pl-9 border-none bg-transparent focus-visible:ring-0" 
          />
        </div>
        <div className="flex items-center gap-2">
            <div className="flex bg-gray-100 p-1 rounded-lg">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setFilterStatus(tab.id)}
                        className={cn(
                            "px-4 py-1.5 text-sm font-medium rounded-md transition-all",
                            filterStatus === tab.id 
                                ? "bg-purple-600 text-white shadow-sm" 
                                : "text-gray-500 hover:text-gray-900"
                        )}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>
            <Button variant="ghost" size="icon" className="text-blue-500 rounded-full hover:bg-blue-50" onClick={handleRefresh}>
                <RefreshCw className="h-4 w-4" />
            </Button>
        </div>
      </div>

      {/* Task Table */}
      <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-gray-50">
            <TableRow>
              <TableHead className="w-[300px]">课程名称</TableHead>
              <TableHead>任务信息</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>时间范围</TableHead>
              <TableHead>进度</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks?.map((task) => (
              <TableRow key={task.id} className="hover:bg-gray-50">
                <TableCell className="font-medium">
                  <div className="flex flex-col gap-1">
                    <span className="text-base text-gray-900">{task.courseName}</span>
                    <div className="flex gap-2">
                        {task.courseTags.map(tag => (
                            <span key={tag} className="text-xs text-gray-500 px-1.5 py-0.5 border rounded bg-white">
                                {tag}
                            </span>
                        ))}
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                    <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium text-gray-700">{task.taskInfo}</span>
                        {task.taskLink && (
                            <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded w-fit">
                                {task.taskLink}
                            </span>
                        )}
                    </div>
                </TableCell>
                <TableCell>
                  <StatusBadge status={task.status} />
                </TableCell>
                <TableCell>
                    <div className="text-xs text-gray-500 flex flex-col">
                        <span>{task.dateRange.start}</span>
                        <span>至 {task.dateRange.end}</span>
                    </div>
                </TableCell>
                <TableCell>
                    <div className="flex flex-col gap-1 w-32">
                        <div className="flex justify-between text-xs">
                            <span className="text-purple-600 font-medium">完成度 {task.progress.completed}/{task.progress.total}</span>
                        </div>
                        <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                            <div 
                                className="h-full bg-purple-500 rounded-full" 
                                style={{ width: `${(task.progress.completed / task.progress.total) * 100}%` }}
                            />
                        </div>
                        {task.progress.score && (
                             <span className="text-xs text-purple-600 font-medium">最近得分: {task.progress.score}分</span>
                        )}
                    </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button 
                        size="sm" 
                        className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white rounded-full px-6"
                        onClick={() =>
                          navigate(`/practice/${task.id}`, {
                            state: {
                              initialNPCDetails: {
                                avatar: "/favicon.svg",
                                tags: task.courseTags.slice(0, 3),
                              },
                            },
                          })
                        }
                    >
                        <Play className="mr-1 h-3 w-3 fill-current" /> 去练习
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full border text-gray-400 hover:text-gray-900">
                        <QrCode className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full border text-gray-400 hover:text-gray-900">
                        <MessageSquare className="h-4 w-4" />
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
