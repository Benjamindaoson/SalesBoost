import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrendingUp, TrendingDown, Users, DollarSign, Target, Activity, AlertTriangle, CheckCircle, Zap, RefreshCw, BarChart3 } from "lucide-react";
import { dealService, CockpitOverview } from '@/services/deal.service';

const EVENT_LABELS: Record<string, string> = {
  deal_created: "新建商机",
  stage_changed: "阶段推进",
  encounter_completed: "完成沟通",
  methodology_updated: "方法论更新",
  risk_alert: "风险预警",
};

const EVENT_ICONS: Record<string, typeof Target> = {
  deal_created: Zap,
  stage_changed: TrendingUp,
  encounter_completed: CheckCircle,
  methodology_updated: Target,
  risk_alert: AlertTriangle,
};

const EVENT_COLORS: Record<string, string> = {
  deal_created: "text-blue-500",
  stage_changed: "text-green-500",
  encounter_completed: "text-indigo-500",
  methodology_updated: "text-purple-500",
  risk_alert: "text-red-500",
};

export default function Cockpit() {
  const [data, setData] = useState<CockpitOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // 每 30 秒刷新
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const d = await dealService.getCockpitOverview();
      setData(d);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  if (loading || !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">总裁驾驶舱</h1>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  const activeFunnel = data.funnel.filter(f => !['closed_won', 'closed_lost'].includes(f.stage));
  const wonCount = data.funnel.find(f => f.stage === 'closed_won')?.count || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">总裁驾驶舱</h1>
          <p className="text-sm text-gray-500">
            实时 · {new Date().toLocaleDateString('zh-CN')}
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={loadData}>
          <RefreshCw className="w-4 h-4" /> 刷新
        </Button>
      </div>

      {/* Row 1: Big Numbers */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            icon: BarChart3, label: "管道商机",
            value: activeFunnel.reduce((s, f) => s + f.count, 0),
            sub: `¥${(activeFunnel.reduce((s, f) => s + f.total_amount, 0) / 10000).toFixed(0)}万`,
            color: "text-blue-600 bg-blue-50",
          },
          {
            icon: DollarSign, label: "赢单预测",
            value: `¥${(data.prediction.predicted_amount / 10000).toFixed(0)}万`,
            sub: `置信度 ${Math.round(data.prediction.confidence * 100)}%`,
            color: "text-green-600 bg-green-50",
          },
          {
            icon: Activity, label: "今日战况",
            value: data.today.encounters_today,
            sub: `新商机 ${data.today.new_deals_today} · 推进 ${data.today.stage_advances_today}`,
            color: "text-amber-600 bg-amber-50",
          },
          {
            icon: Target, label: "方法论均分",
            value: `${Math.round(data.methodology.avg_score)}%`,
            sub: `${data.methodology.total_deals} 个活跃商机`,
            color: "text-purple-600 bg-purple-50",
          },
        ].map((stat, i) => (
          <Card key={i} className="border-0 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stat.color}`}>
                  <stat.icon className="w-5 h-5" />
                </div>
                <span className="text-xs text-gray-500 font-medium">{stat.label}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
              <div className="text-xs text-gray-400 mt-1">{stat.sub}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Row 2: Funnel + Methodology */}
      <div className="grid lg:grid-cols-2 gap-4">
        {/* Funnel */}
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-500" /> 销售漏斗
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activeFunnel.map((f, i) => {
                const maxCount = Math.max(...activeFunnel.map(x => x.count), 1);
                const widthPct = Math.max((f.count / maxCount) * 100, 8);
                const colors = ["bg-blue-400", "bg-cyan-400", "bg-amber-400", "bg-purple-400"];
                return (
                  <div key={f.stage} className="flex items-center gap-3">
                    <span className="w-10 text-xs text-gray-500 text-right">{f.label}</span>
                    <div className="flex-1 relative h-7">
                      <div
                        className={`h-full ${colors[i] || 'bg-gray-300'} rounded-r-lg flex items-center px-3 transition-all`}
                        style={{ width: `${widthPct}%` }}
                      >
                        <span className="text-white text-xs font-semibold">{f.count}</span>
                      </div>
                    </div>
                    <span className="text-xs text-gray-400 w-16 text-right">¥{(f.total_amount / 10000).toFixed(0)}万</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Methodology Stats */}
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Target className="w-4 h-4 text-purple-500" /> MEDDPICC 执行率
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(data.methodology?.dimension_stats ?? []).filter(Boolean).map((dim) => {
                const d = dim!;
                const pct = d.avg_pct ?? 0;
                return (
                <div key={d.dimension ?? ''} className="flex items-center gap-3">
                  <span className="w-20 text-xs text-gray-500 truncate text-right" title={d.label}>
                    {((d.label ?? '').split('(')[0] ?? '').trim().substring(0, 6)}
                  </span>
                  <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pct > 70 ? 'bg-green-400' : pct > 40 ? 'bg-amber-400' : 'bg-red-400'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-gray-600 w-10 text-right">{Math.round(pct)}%</span>
                </div>
              );})}
            </div>
            {data.methodology.insight && (
              <div className="mt-4 bg-red-50 rounded-lg p-3 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <div className="text-xs text-red-700">{data.methodology.insight}</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Event Feed */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Activity className="w-4 h-4 text-green-500" /> 实时动态
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.recent_events.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">暂无动态</div>
          ) : (
            <div className="space-y-2">
              {data.recent_events.map(ev => {
                const Icon = EVENT_ICONS[ev.event_type] || Activity;
                const color = EVENT_COLORS[ev.event_type] || "text-gray-500";
                const payload = ev.payload || {};
                const customerName = (payload as any).customer_name || '';

                let description = EVENT_LABELS[ev.event_type] || ev.event_type;
                if (ev.event_type === 'stage_changed') {
                  description = `${customerName} 推进到 ${(payload as any).to || ''}`;
                } else if (ev.event_type === 'methodology_updated') {
                  description = `${customerName} 方法论分 ${(payload as any).score || 0}%`;
                } else if (ev.event_type === 'deal_created') {
                  description = `新建商机 ${customerName}`;
                } else if (ev.event_type === 'encounter_completed') {
                  description = `${customerName} 完成${(payload as any).encounter_type === 'live' ? '实战' : '准备'}沟通`;
                }

                return (
                  <div key={ev.id} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                    <Icon className={`w-4 h-4 shrink-0 ${color}`} />
                    <span className="text-sm text-gray-700 flex-1">{description}</span>
                    <span className="text-[10px] text-gray-400 shrink-0">
                      {ev.created_at ? new Date(ev.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
