import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Target, Plus, Swords, BookOpen, TrendingUp, ChevronRight, Users, DollarSign, Activity } from "lucide-react";
import { dealService, Deal, FunnelItem } from '@/services/deal.service';

const STAGE_LABELS: Record<string, string> = {
  lead: "线索", qualified: "机会", proposal: "方案",
  negotiation: "谈判", closed_won: "成交", closed_lost: "流失",
};

const STAGE_COLORS: Record<string, string> = {
  lead: "bg-blue-100 text-blue-700",
  qualified: "bg-cyan-100 text-cyan-700",
  proposal: "bg-amber-100 text-amber-700",
  negotiation: "bg-purple-100 text-purple-700",
  closed_won: "bg-green-100 text-green-700",
  closed_lost: "bg-red-100 text-red-700",
};

export default function BattleCenter() {
  const navigate = useNavigate();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [funnel, setFunnel] = useState<FunnelItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [d, f] = await Promise.all([
        dealService.list(),
        dealService.getFunnel(),
      ]);
      setDeals(Array.isArray(d) ? d : []);
      setFunnel(Array.isArray(f) ? f : []);
    } catch (e) {
      console.error('Failed to load battle center data', e);
    } finally {
      setLoading(false);
    }
  }

  const activeDeals = deals.filter(d => !['closed_won', 'closed_lost'].includes(d.stage));
  const totalAmount = activeDeals.reduce((s, d) => s + (d.amount || 0), 0);
  const avgScore = activeDeals.length
    ? Math.round(activeDeals.reduce((s, d) => s + (d.methodology_score || 0), 0) / activeDeals.length)
    : 0;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">作战中心</h1>
          <p className="text-gray-500 mt-1">掌握全局，赢得每一单</p>
        </div>
        <Button onClick={() => navigate('/student/pipeline')} className="gap-2 rounded-full bg-indigo-600 hover:bg-indigo-700">
          <Plus className="w-4 h-4" /> 新建商机
        </Button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Users, label: "活跃商机", value: activeDeals.length, color: "text-blue-600 bg-blue-50" },
          { icon: DollarSign, label: "管道金额", value: `¥${(totalAmount / 10000).toFixed(1)}万`, color: "text-green-600 bg-green-50" },
          { icon: Target, label: "平均方法论分", value: `${avgScore}%`, color: "text-purple-600 bg-purple-50" },
          { icon: Activity, label: "本月沟通", value: deals.reduce((s, d) => s + (d.encounter_count || 0), 0), color: "text-amber-600 bg-amber-50" },
        ].map((stat, i) => (
          <Card key={i} className="border-0 shadow-sm">
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                <div className="text-xs text-gray-500">{stat.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Mini Funnel */}
      {funnel.length > 0 && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-500" /> 销售漏斗
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-4">
            <div className="flex items-end gap-1 h-16">
              {funnel.map((f, i) => {
                const maxCount = Math.max(...funnel.map(x => x.count), 1);
                const h = Math.max((f.count / maxCount) * 100, 8);
                const colors = ["bg-blue-400", "bg-cyan-400", "bg-amber-400", "bg-purple-400"];
                return (
                  <div key={f.stage} className="flex-1 flex flex-col items-center gap-1">
                    <div className={`w-full rounded-t ${colors[i] || 'bg-gray-300'} transition-all`} style={{ height: `${h}%` }} />
                    <span className="text-[10px] text-gray-500">{f.count}</span>
                    <span className="text-[10px] text-gray-400">{STAGE_LABELS[f.stage] || f.stage}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: BookOpen, label: "战前准备", desc: "选择商机，生成作战计划", path: "/student/pipeline", color: "from-blue-500 to-indigo-600" },
          { icon: Swords, label: "实战辅助", desc: "实时对话中获取 AI 建议", path: "/student/live-assist", color: "from-purple-500 to-pink-600" },
          { icon: Target, label: "战后复盘", desc: "查看复盘报告和改进建议", path: "/student/review", color: "from-amber-500 to-orange-600" },
        ].map((action) => (
          <Card
            key={action.label}
            className="border-0 shadow-sm cursor-pointer hover:shadow-md transition-all group"
            onClick={() => navigate(action.path)}
          >
            <CardContent className="p-5 flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center text-white shadow-lg`}>
                <action.icon className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-gray-900">{action.label}</div>
                <div className="text-xs text-gray-500">{action.desc}</div>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-gray-500 transition-colors" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Active Deals */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-semibold text-gray-700">我的商机</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => navigate('/student/pipeline')} className="text-xs text-indigo-600">
            查看全部 <ChevronRight className="w-3 h-3 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : activeDeals.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p>暂无活跃商机</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => navigate('/student/pipeline')}>
                创建第一个商机
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {activeDeals.slice(0, 6).map(deal => (
                <div
                  key={deal.id}
                  className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/student/battle-prep/${deal.id}`)}
                >
                  <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-sm">
                    {deal.customer_name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 text-sm truncate">{deal.customer_name}</div>
                    <div className="text-xs text-gray-400">{deal.customer_company || '未填写公司'}</div>
                  </div>
                  <Badge className={`text-[10px] ${STAGE_COLORS[deal.stage] || 'bg-gray-100 text-gray-600'}`}>
                    {STAGE_LABELS[deal.stage] || deal.stage}
                  </Badge>
                  <div className="w-20 flex items-center gap-1">
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full transition-all"
                        style={{ width: `${deal.methodology_score || 0}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-400 w-7 text-right">{Math.round(deal.methodology_score || 0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
