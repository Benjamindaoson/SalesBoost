import { HistoryStats } from '@/types/business';
import { Card, CardContent } from "@/components/ui/card";
import { RotateCcw, TrendingUp, Award, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HistoryStatsProps {
  stats: HistoryStats;
}

export function HistoryStatsCards({ stats }: HistoryStatsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="总排练次数"
        value={stats.totalRehearsals}
        subtitle="累计排练记录"
        icon={RotateCcw}
        iconColor="text-purple-600"
        iconBgColor="bg-purple-50"
      />
      <StatCard
        title="平均分数"
        value={stats.averageScore}
        subtitle="保持进步"
        icon={TrendingUp}
        iconColor="text-blue-500"
        iconBgColor="bg-blue-50"
      />
      <StatCard
        title="最高分数"
        value={stats.bestScore}
        subtitle="优秀表现"
        icon={Award}
        iconColor="text-green-500"
        iconBgColor="bg-green-50"
      />
      <StatCard
        title="总练习时长"
        value={stats.totalDurationMinutes}
        subtitle="分钟"
        icon={Clock}
        iconColor="text-yellow-500"
        iconBgColor="bg-yellow-50"
      />
    </div>
  );
}

function StatCard({ title, value, subtitle, icon: Icon, iconColor, iconBgColor }: any) {
  return (
    <Card className="border-none shadow-sm hover:shadow-md transition-shadow duration-300">
      <CardContent className="p-6 flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <div className="text-3xl font-bold text-gray-900">{value}</div>
          <p className="text-xs text-gray-400">{subtitle}</p>
        </div>
        <div className={cn("p-2 rounded-xl", iconBgColor)}>
          <Icon className={cn("w-5 h-5", iconColor)} />
        </div>
      </CardContent>
    </Card>
  );
}
