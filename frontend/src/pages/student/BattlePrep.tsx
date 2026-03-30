import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Target, Shield, AlertCircle, CheckCircle, Copy, Play, Sparkles, Loader2, ChevronRight, Circle } from "lucide-react";
import { dealService, Deal, MethodologyDetail, GapItem, PrepPrompt } from '@/services/deal.service';
import { useToast } from "@/hooks/use-toast";

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  confirmed: { icon: CheckCircle, color: "text-green-500", label: "已确认" },
  partial: { icon: AlertCircle, color: "text-amber-500", label: "部分确认" },
  unknown: { icon: Circle, color: "text-red-400", label: "未知" },
};

export default function BattlePrep() {
  const { dealId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [deal, setDeal] = useState<Deal | null>(null);
  const [methodology, setMethodology] = useState<MethodologyDetail | null>(null);
  const [prepPrompt, setPrepPrompt] = useState<PrepPrompt | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPrep, setLoadingPrep] = useState(false);
  const [activeTab, setActiveTab] = useState<'check' | 'ammo' | 'sim'>('check');
  const [editingDim, setEditingDim] = useState<string | null>(null);
  const [editEvidence, setEditEvidence] = useState("");
  const [editStatus, setEditStatus] = useState("unknown");

  const id = parseInt(dealId || '0');

  useEffect(() => {
    if (id) loadData();
  }, [id]);

  async function loadData() {
    try {
      const [d, m] = await Promise.all([
        dealService.get(id),
        dealService.getMethodology(id),
      ]);
      setDeal(d);
      setMethodology(m);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function loadPrep() {
    setLoadingPrep(true);
    try {
      const p = await dealService.getPrepPrompt(id);
      setPrepPrompt(p);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingPrep(false);
    }
  }

  async function handleUpdateDimension(dim: string) {
    try {
      await dealService.updateDimension(id, dim, editStatus, editEvidence);
      toast({ title: "已更新" });
      setEditingDim(null);
      const m = await dealService.getMethodology(id);
      setMethodology(m);
    } catch (e) {
      toast({ title: "更新失败", variant: "destructive" });
    }
  }

  function copyText(text: string) {
    navigator.clipboard.writeText(text);
    toast({ title: "已复制" });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!deal) {
    return (
      <div className="text-center py-20 text-gray-400">
        <Target className="w-12 h-12 mx-auto mb-4 opacity-40" />
        <p>商机不存在</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/student/pipeline')}>返回漏斗</Button>
      </div>
    );
  }

  const dims = methodology?.dimensions || {};
  const gaps = methodology?.gaps || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
            <span className="cursor-pointer hover:text-gray-600" onClick={() => navigate('/student/pipeline')}>漏斗</span>
            <ChevronRight className="w-3 h-3" />
            <span>战前准备</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Shield className="w-6 h-6 text-indigo-500" />
            {deal.customer_name}
            {deal.customer_company && <span className="text-base font-normal text-gray-400">· {deal.customer_company}</span>}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-2xl font-bold text-indigo-600">{Math.round(methodology?.overall_score || 0)}%</div>
            <div className="text-xs text-gray-400">方法论完成度</div>
          </div>
          <div className="w-16 h-16 relative">
            <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" strokeWidth="3" />
              <circle
                cx="18" cy="18" r="15.5" fill="none" stroke="#6366f1" strokeWidth="3"
                strokeDasharray={`${(methodology?.overall_score || 0) * 0.974} 97.4`}
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {[
          { key: 'check' as const, label: '方法论检查', icon: Target },
          { key: 'ammo' as const, label: '话术弹药库', icon: Sparkles },
          { key: 'sim' as const, label: '模拟演练', icon: Play },
        ].map(tab => (
          <button
            key={tab.key}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => {
              setActiveTab(tab.key);
              if (tab.key === 'ammo' && !prepPrompt) loadPrep();
            }}
          >
            <tab.icon className="w-4 h-4" /> {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'check' && (
        <div className="space-y-4">
          {/* Next Focus */}
          {methodology?.next_focus && (
            <Card className="border-indigo-200 bg-indigo-50/50">
              <CardContent className="p-4 flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-indigo-500 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-indigo-700">AI 建议本次重点</div>
                  <div className="text-sm text-indigo-600">
                    补全 <strong>{dims[methodology.next_focus]?.status === 'unknown' ? '' : ''}
                    {gaps.find(g => g.dimension === methodology.next_focus)?.label || methodology.next_focus}</strong>
                    {' — '}
                    {gaps.find(g => g.dimension === methodology.next_focus)?.description || ''}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Dimensions Grid */}
          <div className="grid gap-3">
            {Object.entries(dims).map(([key, dim]) => {
              const cfg = STATUS_CONFIG[dim.status] ?? STATUS_CONFIG.unknown!;
              const Icon = cfg.icon;
              const gap = gaps.find(g => g.dimension === key);
              const isEditing = editingDim === key;

              return (
                <Card key={key} className="border-0 shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${cfg.color}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <div className="font-medium text-gray-900 text-sm">{gap?.label || key}</div>
                          <Badge variant="outline" className={`text-[10px] ${cfg.color}`}>{cfg.label}</Badge>
                        </div>
                        {gap && <div className="text-xs text-gray-400 mt-0.5">{gap.description}</div>}
                        {dim.evidence && <div className="text-xs text-gray-600 mt-1 bg-gray-50 rounded px-2 py-1">{dim.evidence}</div>}

                        {isEditing ? (
                          <div className="mt-2 flex gap-2 items-end">
                            <select
                              className="border rounded px-2 py-1 text-xs"
                              value={editStatus}
                              onChange={e => setEditStatus(e.target.value)}
                            >
                              <option value="unknown">未知</option>
                              <option value="partial">部分确认</option>
                              <option value="confirmed">已确认</option>
                            </select>
                            <Input
                              className="text-xs h-7 flex-1"
                              placeholder="证据/备注"
                              value={editEvidence}
                              onChange={e => setEditEvidence(e.target.value)}
                            />
                            <Button size="sm" className="h-7 text-xs" onClick={() => handleUpdateDimension(key)}>保存</Button>
                            <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setEditingDim(null)}>取消</Button>
                          </div>
                        ) : (
                          <button
                            className="text-xs text-indigo-500 mt-1 hover:underline"
                            onClick={() => { setEditingDim(key); setEditStatus(dim.status); setEditEvidence(""); }}
                          >
                            更新状态
                          </button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'ammo' && (
        <div className="space-y-4">
          {loadingPrep ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-500 mr-2" />
              <span className="text-gray-500">AI 正在生成话术弹药...</span>
            </div>
          ) : prepPrompt ? (
            <>
              <Card className="border-0 shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-500" /> 作战计划
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">{prepPrompt.prompt}</pre>
                </CardContent>
              </Card>

              {prepPrompt.gaps.slice(0, 3).map((gap, i) => (
                <Card key={i} className="border-0 shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium text-sm text-gray-900">{gap.label}</div>
                        <div className="text-xs text-gray-400">{gap.description}</div>
                      </div>
                      <Badge variant="outline" className="text-[10px]">优先级 {i + 1}</Badge>
                    </div>
                    {gap.probe_questions.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {gap.probe_questions.map((q, j) => (
                          <div key={j} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded px-3 py-2">
                            <span className="flex-1">{q}</span>
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => copyText(q)}>
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}

              <Button variant="outline" onClick={loadPrep} className="gap-2">
                <Sparkles className="w-4 h-4" /> 重新生成
              </Button>
            </>
          ) : (
            <div className="text-center py-16 text-gray-400">
              <Sparkles className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p>点击生成话术弹药库</p>
              <Button className="mt-3" onClick={loadPrep}>生成作战计划</Button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'sim' && (
        <Card className="border-0 shadow-sm">
          <CardContent className="py-12 text-center">
            <Play className="w-16 h-16 mx-auto mb-4 text-indigo-300" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">模拟演练</h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              与 AI 模拟客户进行对话演练，重点突破方法论中的薄弱环节
            </p>
            {gaps.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-center mb-6">
                {gaps.slice(0, 3).map(g => (
                  <Badge key={g.dimension} variant="outline" className="text-xs">{g.label}</Badge>
                ))}
              </div>
            )}
            <Button
              size="lg"
              className="gap-2 bg-indigo-600 hover:bg-indigo-700 rounded-full px-8"
              onClick={() => navigate(`/student/training?dealId=${id}`)}
            >
              <Play className="w-5 h-5" /> 开始演练
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
