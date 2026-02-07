import { useState, useEffect } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowUp, Users, Trophy, Activity, ChevronRight, DollarSign, Clock } from "lucide-react";
import { analyticsService, AnalyticsOverview } from '@/services/analytics.service';

export default function AdminAnalysis() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const result = await analyticsService.getOverview();
        setData(result);
      } catch (error) {
        console.error("Failed to fetch analytics", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-gray-500">加载分析数据中...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-red-500">数据加载失败</div>;
  }

  // Transform API data to UI format
  const KPI_DATA = [
    {
      title: "总消耗 (USD)",
      value: `$${data.total_cost_usd.toFixed(4)}`,
      subtext: "本周累计",
      icon: DollarSign,
      iconColor: "text-purple-600",
      bg: "bg-purple-50"
    },
    {
      title: "活跃用户 (7天)",
      value: data.active_users_7d.toString(),
      subtext: "较上周 +5%",
      icon: Users,
      iconColor: "text-blue-600",
      bg: "bg-blue-50"
    },
    {
      title: "能力指数",
      value: data.competency_index.toFixed(1),
      subtext: "整体水平良好",
      icon: Trophy,
      iconColor: "text-green-600",
      bg: "bg-green-50"
    },
    {
      title: "训练时长 (7天)",
      value: `${Math.round(data.total_practice_seconds_7d / 60)}`,
      subtext: "分钟",
      icon: Clock,
      iconColor: "text-orange-600",
      bg: "bg-orange-50"
    }
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">能力分析</h1>
        <p className="text-sm text-gray-500 mt-1">查看学员能力分析数据 (实时)</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {KPI_DATA.map((kpi, idx) => (
          <Card key={idx} className="border-none shadow-sm hover:shadow-md transition-shadow">
            <CardContent className="p-6 flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 mb-1">{kpi.title}</p>
                <div className="text-3xl font-bold text-gray-900 mb-1">{kpi.value}</div>
                <p className="text-xs text-gray-400">{kpi.subtext}</p>
              </div>
              <div className={`p-3 rounded-xl ${kpi.bg}`}>
                <kpi.icon className={`w-6 h-6 ${kpi.iconColor}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Skill Averages */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6">
            <h3 className="text-lg font-medium mb-4">开场白能力</h3>
            <div className="text-4xl font-bold text-blue-600">{data.skill_averages.opening.toFixed(1)} <span className="text-sm text-gray-400 font-normal">/ 10</span></div>
        </Card>
        <Card className="p-6">
            <h3 className="text-lg font-medium mb-4">需求发现</h3>
            <div className="text-4xl font-bold text-purple-600">{data.skill_averages.discovery.toFixed(1)} <span className="text-sm text-gray-400 font-normal">/ 10</span></div>
        </Card>
        <Card className="p-6">
            <h3 className="text-lg font-medium mb-4">缔结成交</h3>
            <div className="text-4xl font-bold text-green-600">{data.skill_averages.closing.toFixed(1)} <span className="text-sm text-gray-400 font-normal">/ 10</span></div>
        </Card>
      </div>
    </div>
  );
}
