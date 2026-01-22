import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, BookOpen, MessageSquare, TrendingUp } from "lucide-react";

export default function DashboardPage() {
  const stats = [
    { label: "总学员数", value: "128", icon: Users, color: "text-blue-600" },
    { label: "活跃课程", value: "12", icon: BookOpen, color: "text-purple-600" },
    { label: "今日对练", value: "45", icon: MessageSquare, color: "text-green-600" },
    { label: "平均得分", value: "8.4", icon: TrendingUp, color: "text-orange-600" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">管理概览</h1>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">
                {stat.label}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>最近活跃租户</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-500">图表组件待集成...</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>训练完成率趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-500">图表组件待集成...</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
