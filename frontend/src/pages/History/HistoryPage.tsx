import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { historyService } from "@/services/api";
import { StatCard } from "@/components/common/StatCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Search, Download, RefreshCw, LineChart, Award, Clock, Eye, RotateCcw, Calendar, Filter } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { EvaluationReport } from "./EvaluationReport";

export default function HistoryPage() {
  const navigate = useNavigate();
  const [reportOpen, setReportOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<any>(null);

  const { data: stats } = useQuery({
    queryKey: ['historyStats'],
    queryFn: historyService.getStats
  });
// ...

  const { data: records } = useQuery({
    queryKey: ['historyRecords'],
    queryFn: () => historyService.getHistory()
  });

  const getScoreColor = (score: number) => {
      if (score >= 90) return "text-green-600 border-green-200 bg-green-50";
      if (score >= 80) return "text-blue-600 border-blue-200 bg-blue-50";
      return "text-orange-600 border-orange-200 bg-orange-50";
  };

  const handleExport = () => {
    if (!records || records.length === 0) {
      alert("暂无数据可导出");
      return;
    }
    
    const headers = ["ID,日期时间,课程信息,客户角色,类别,时长,得分"];
    const rows = records.map((record: any) => {
      return [
        record.id,
        record.dateTime,
        record.courseInfo,
        record.customerRole,
        record.category,
        record.duration,
        record.score
      ].map(field => `"${field}"`).join(",");
    });
    
    const csvContent = "\ufeff" + [headers, ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `practice_history_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">历史记录</h2>
        <p className="text-gray-500">查看所有练习记录</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard 
          label="总陪练次数" 
          subLabel="累计陪练记录"
          value={stats?.totalSessions || 0} 
          icon={RefreshCw}
          iconClassName="text-purple-600"
          iconBgColor="bg-purple-100"
        />
        <StatCard 
          label="平均分数" 
          subLabel="保持进步"
          value={stats?.averageScore || 0} 
          icon={LineChart}
          iconClassName="text-blue-500"
          iconBgColor="bg-blue-100"
        />
        <StatCard 
          label="最高分数" 
          subLabel="优秀表现"
          value={stats?.highestScore || 0} 
          icon={Award}
          iconClassName="text-green-500"
          iconBgColor="bg-green-100"
        />
        <StatCard 
          label="总练习时长" 
          subLabel="分钟"
          value={stats?.totalDuration || 0} 
          icon={Clock}
          iconClassName="text-orange-500"
          iconBgColor="bg-orange-100"
        />
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white p-2 rounded-lg shadow-sm">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input 
            placeholder="搜索课程名称、客户名称、类别..." 
            className="pl-9 border-none bg-transparent focus-visible:ring-0" 
          />
        </div>
        <div className="flex items-center gap-2">
            <Button variant="outline" className="text-gray-500 border-gray-200">
                <Calendar className="mr-2 h-4 w-4" /> 全部时间
            </Button>
            <Button variant="outline" className="text-gray-500 border-gray-200">
                <Filter className="mr-2 h-4 w-4" /> 全部分数
            </Button>
            <Button variant="outline" className="text-gray-500 border-gray-200" onClick={handleExport}>
                <Download className="mr-2 h-4 w-4" /> 导出
            </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-gray-50">
            <TableRow>
              <TableHead>日期时间</TableHead>
              <TableHead>课程信息</TableHead>
              <TableHead>客户角色</TableHead>
              <TableHead>类别</TableHead>
              <TableHead>时长</TableHead>
              <TableHead>得分</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {records?.map((record) => (
              <TableRow key={record.id} className="hover:bg-gray-50">
                <TableCell className="text-gray-500 text-sm">
                    <div className="flex items-center gap-2">
                        <Calendar className="h-3 w-3" />
                        {record.dateTime}
                    </div>
                </TableCell>
                <TableCell className="font-medium text-gray-900">{record.courseInfo}</TableCell>
                <TableCell>
                    <div className="flex flex-col">
                        <span className="text-gray-900">{record.customerRole}</span>
                        <span className="text-xs text-gray-400">27岁，互联网行业</span> {/* Mock detail */}
                    </div>
                </TableCell>
                <TableCell>
                    <Badge variant="secondary" className="bg-purple-50 text-purple-600 hover:bg-purple-100 font-normal">
                        {record.category}
                    </Badge>
                </TableCell>
                <TableCell className="text-gray-500 flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {record.duration}
                </TableCell>
                <TableCell>
                    <div className={cn("inline-flex items-center justify-center w-10 h-10 rounded-lg text-lg font-bold border", getScoreColor(record.score))}>
                        {record.score}
                    </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button 
                        variant="outline" 
                        size="sm" 
                        className="text-gray-600 rounded-full"
                        onClick={() => {
                            setSelectedRecord(record);
                            setReportOpen(true);
                        }}
                    >
                        <Eye className="mr-1 h-3 w-3" /> 查看详情
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8 rounded-full text-gray-600"
                      onClick={() =>
                        navigate(`/practice/${record.id}`, {
                          state: {
                            initialNPCDetails: {
                              avatar: "/favicon.svg",
                              tags: [record.category].slice(0, 3),
                            },
                          },
                        })
                      }
                    >
                        <RotateCcw className="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      
      <EvaluationReport 
        open={reportOpen} 
        onOpenChange={setReportOpen} 
        data={selectedRecord ? {
            score: selectedRecord.score,
            improvement: Math.floor(Math.random() * 10) + 1, // Mock improvement
            scenario: selectedRecord.courseInfo + "·" + selectedRecord.customerRole,
            dimensions: [
                { name: "开场破冰", score: Math.min(100, selectedRecord.score + 5), change: 8, status: "up" },
                { name: "产品介绍", score: Math.max(60, selectedRecord.score - 5), change: 5, status: "up" },
                { name: "客户洞察", score: selectedRecord.score, change: 10, status: "up" },
                { name: "异议处理", score: Math.max(60, selectedRecord.score - 10), change: -2, status: "down" },
                { name: "权益推荐", score: Math.min(100, selectedRecord.score + 2), change: 12, status: "up" },
                { name: "合规表达", score: selectedRecord.score, change: 3, status: "up" },
                { name: "收尾促成", score: Math.max(60, selectedRecord.score - 5), change: 0, status: "flat" },
                { name: "情绪安抚", score: Math.min(100, selectedRecord.score + 3), change: 6, status: "up" },
            ]
        } : undefined}
      />
    </div>
  );
}
