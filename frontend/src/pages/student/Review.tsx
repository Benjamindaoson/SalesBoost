import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, TrendingUp, TrendingDown, CheckCircle, AlertCircle, Target, ArrowRight, Clock, ChevronRight, Circle } from "lucide-react";
import { dealService, Deal, Encounter } from '@/services/deal.service';

const STAGE_LABELS: Record<string, string> = {
  lead: "线索", qualified: "机会", proposal: "方案",
  negotiation: "谈判", closed_won: "成交", closed_lost: "流失",
};

const TYPE_LABELS: Record<string, string> = {
  prep: "战前准备", live: "实战沟通", review: "战后复盘",
};

const TYPE_COLORS: Record<string, string> = {
  prep: "bg-blue-100 text-blue-700",
  live: "bg-green-100 text-green-700",
  review: "bg-amber-100 text-amber-700",
};

export default function Review() {
  const navigate = useNavigate();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [encounters, setEncounters] = useState<Record<number, Encounter[]>>({});
  const [expandedDeal, setExpandedDeal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const d = await dealService.list();
      setDeals(Array.isArray(d) ? d : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function toggleDeal(dealId: number) {
    if (expandedDeal === dealId) {
      setExpandedDeal(null);
      return;
    }
    setExpandedDeal(dealId);
    if (!encounters[dealId]) {
      try {
        const encs = await dealService.listEncounters(dealId);
        setEncounters(prev => ({ ...prev, [dealId]: Array.isArray(encs) ? encs : [] }));
      } catch (e) {
        console.error(e);
      }
    }
  }

  function renderScoreDelta(before: any, after: any) {
    if (!before || !after) return null;
    const scoreBefore = before.overall_score || 0;
    const scoreAfter = after.overall_score || 0;
    const delta = scoreAfter - scoreBefore;

    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">{Math.round(scoreBefore)}%</span>
        <ArrowRight className="w-3 h-3 text-gray-400" />
        <span className="text-sm font-semibold text-gray-900">{Math.round(scoreAfter)}%</span>
        {delta !== 0 && (
          <span className={`text-xs font-semibold ${delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {delta > 0 ? '+' : ''}{delta.toFixed(1)}%
          </span>
        )}
      </div>
    );
  }

  function renderDimensionChanges(before: any, after: any) {
    if (!before?.dimensions || !after?.dimensions) return null;
    const changes: { key: string; from: string; to: string; label: string }[] = [];

    for (const [key, afterDim] of Object.entries(after.dimensions) as [string, any][]) {
      const beforeDim = before.dimensions[key];
      if (beforeDim && beforeDim.status !== afterDim.status) {
        changes.push({ key, from: beforeDim.status, to: afterDim.status, label: key });
      }
    }

    if (changes.length === 0) return <div className="text-xs text-gray-400">无维度变化</div>;

    const statusIcon = (s: string) => {
      if (s === 'confirmed') return <CheckCircle className="w-3 h-3 text-green-500" />;
      if (s === 'partial') return <AlertCircle className="w-3 h-3 text-amber-500" />;
      return <Circle className="w-3 h-3 text-red-400" />;
    };

    return (
      <div className="space-y-1">
        {changes.map(c => (
          <div key={c.key} className="flex items-center gap-2 text-xs">
            {statusIcon(c.from)}
            <ArrowRight className="w-3 h-3 text-gray-300" />
            {statusIcon(c.to)}
            <span className="text-gray-600">{c.label}</span>
          </div>
        ))}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 rounded-lg animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">战后复盘</h1>
        <p className="text-gray-500 mt-1">每次沟通都是成长机会</p>
      </div>

      {deals.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>暂无复盘记录</p>
          <Button variant="outline" className="mt-3" onClick={() => navigate('/student/pipeline')}>
            创建商机开始
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {deals.map(deal => {
            const isExpanded = expandedDeal === deal.id;
            const encs = encounters[deal.id] || [];

            return (
              <Card key={deal.id} className="border-0 shadow-sm overflow-hidden">
                <div
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleDeal(deal.id)}
                >
                  <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-sm shrink-0">
                    {deal.customer_name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 text-sm">{deal.customer_name}</div>
                    <div className="text-xs text-gray-400">{deal.customer_company || '—'}</div>
                  </div>
                  <Badge variant="outline" className="text-[10px]">{STAGE_LABELS[deal.stage] || deal.stage}</Badge>
                  <div className="w-20 flex items-center gap-1">
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${deal.methodology_score || 0}%` }} />
                    </div>
                    <span className="text-[10px] text-gray-400">{Math.round(deal.methodology_score || 0)}%</span>
                  </div>
                  <div className="text-xs text-gray-400 flex items-center gap-1">
                    <FileText className="w-3 h-3" /> {deal.encounter_count || 0}
                  </div>
                  <ChevronRight className={`w-4 h-4 text-gray-300 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-100 bg-gray-50/50 px-5 py-3">
                    {encs.length === 0 ? (
                      <div className="text-center py-6 text-gray-400 text-sm">
                        暂无沟通记录
                        <Button variant="link" size="sm" onClick={() => navigate(`/student/battle-prep/${deal.id}`)}>
                          去准备
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {encs.map(enc => (
                          <Card key={enc.id} className="border bg-white shadow-none">
                            <CardContent className="p-4">
                              <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <Badge className={`text-[10px] ${TYPE_COLORS[enc.encounter_type] || 'bg-gray-100 text-gray-600'}`}>
                                    {TYPE_LABELS[enc.encounter_type] || enc.encounter_type}
                                  </Badge>
                                  <span className="text-xs text-gray-400 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {enc.created_at ? new Date(enc.created_at).toLocaleString('zh-CN') : '—'}
                                  </span>
                                </div>
                                {renderScoreDelta(enc.methodology_before, enc.methodology_after)}
                              </div>

                              {enc.summary && (
                                <div className="text-sm text-gray-700 mb-2">{enc.summary}</div>
                              )}

                              {renderDimensionChanges(enc.methodology_before, enc.methodology_after)}

                              {enc.action_items && (
                                <div className="mt-2 text-xs text-gray-500 bg-gray-50 rounded p-2">
                                  <strong>下一步：</strong> {enc.action_items}
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}

                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline" className="text-xs" onClick={() => navigate(`/student/battle-prep/${deal.id}`)}>
                        安排下次准备
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
