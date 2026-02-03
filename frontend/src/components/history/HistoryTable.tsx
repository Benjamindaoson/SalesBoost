import { HistoryRecord } from '@/types/business';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Eye, RotateCcw, Calendar, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HistoryTableProps {
  records: HistoryRecord[];
}

export function HistoryTable({ records }: HistoryTableProps) {
  const getScoreColor = (score: number) => {
    if (score >= 90) return "bg-green-50 text-green-600 border-green-100";
    if (score >= 80) return "bg-blue-50 text-blue-600 border-blue-100";
    if (score >= 70) return "bg-yellow-50 text-yellow-600 border-yellow-100";
    return "bg-red-50 text-red-600 border-red-100";
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case '新客户开发': return "bg-purple-50 text-purple-600";
      case '异议处理': return "bg-pink-50 text-pink-600";
      case '需求挖掘': return "bg-indigo-50 text-indigo-600";
      case '合同签署': return "bg-blue-50 text-blue-600";
      default: return "bg-gray-50 text-gray-600";
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100">
      <Table>
        <TableHeader className="bg-gray-50/50">
          <TableRow>
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
            <TableRow key={record.id} className="hover:bg-muted/30 transition-colors">
              <TableCell>
                <div className="flex items-center text-gray-500 text-sm gap-2">
                  <Calendar className="w-3.5 h-3.5 text-gray-400" />
                  <div className="flex flex-col">
                    <span>{record.dateTime.split(' ')[0]}</span>
                    <span className="text-xs text-gray-400">{record.dateTime.split(' ')[1]}</span>
                  </div>
                </div>
              </TableCell>
              <TableCell className="font-medium text-gray-700">{record.courseName}</TableCell>
              <TableCell>
                <div className="flex flex-col">
                  <span className="text-gray-900 font-medium">{record.customerName}</span>
                  <span className="text-xs text-gray-400 mt-0.5">{record.customerRole}</span>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="secondary" className={cn("font-normal rounded-md", getCategoryColor(record.category))}>
                  {record.category}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center text-gray-500 text-sm gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  {record.duration}
                </div>
              </TableCell>
              <TableCell>
                <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg border", getScoreColor(record.score))}>
                  {record.score}
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-gray-600 hover:text-gray-900 border-gray-200">
                    <Eye className="w-3.5 h-3.5" /> 查看详情
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-full">
                    <RotateCcw className="w-4 h-4" />
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
