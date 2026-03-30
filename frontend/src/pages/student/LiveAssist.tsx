import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Send, Sparkles, Copy, Loader2, Zap, Shield, Target,
  MessageSquare, Brain, TrendingUp, AlertTriangle, Info,
  CheckCircle2, ChevronRight, User
} from "lucide-react";
import { dealService, Deal, CopilotSuggestion, CopilotResponse } from '@/services/deal.service';
import { useAuthStore } from '@/store/auth.store';
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

// -------------------------------------------------------------------
// Constants
// -------------------------------------------------------------------

const STAGE_LABELS: Record<string, string> = {
  opening: "开场", discovery: "需求挖掘", pitch: "产品介绍",
  objection_handling: "异议处理", closing: "成交推进",
};

const STAGE_COLORS: Record<string, string> = {
  opening: "bg-blue-500/15 text-blue-600 border-blue-200",
  discovery: "bg-cyan-500/15 text-cyan-600 border-cyan-200",
  pitch: "bg-amber-500/15 text-amber-600 border-amber-200",
  objection_handling: "bg-red-500/15 text-red-600 border-red-200",
  closing: "bg-emerald-500/15 text-emerald-600 border-emerald-200",
};

const INTENT_META: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  OBJECTION: { label: "异议", color: "text-red-500 bg-red-50 border-red-200", icon: AlertTriangle },
  BUYING_SIGNAL: { label: "购买信号", color: "text-emerald-600 bg-emerald-50 border-emerald-200", icon: TrendingUp },
  DISCOVERY: { label: "信息探索", color: "text-cyan-600 bg-cyan-50 border-cyan-200", icon: MessageSquare },
  ECONOMIC_BUYER_GAP: { label: "决策缺口", color: "text-purple-600 bg-purple-50 border-purple-200", icon: Target },
  CLARIFICATION: { label: "澄清请求", color: "text-blue-600 bg-blue-50 border-blue-200", icon: Info },
  SOCIAL: { label: "社交互动", color: "text-gray-500 bg-gray-50 border-gray-200", icon: User },
  UNKNOWN: { label: "未知意图", color: "text-gray-400 bg-gray-50 border-gray-200", icon: MessageSquare },
};

// -------------------------------------------------------------------
// Subcomponents
// -------------------------------------------------------------------

interface IntentBadgeProps {
  intentType: string;
  confidence: number;
}
function IntentBadge({ intentType, confidence }: IntentBadgeProps) {
  const meta = INTENT_META[intentType] || INTENT_META.UNKNOWN;
  const Icon = meta.icon;
  return (
    <div className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold", meta.color)}>
      <Icon className="w-3.5 h-3.5" />
      {meta.label}
      <span className="opacity-70">· {Math.round(confidence * 100)}%</span>
    </div>
  );
}

interface ConfidenceBarProps {
  value: number; // 0–1
  label?: string;
}
function ConfidenceBar({ value, label }: ConfidenceBarProps) {
  const pct = Math.round(value * 100);
  const color = pct >= 75 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      {label && <span className="shrink-0">{label}</span>}
      <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-semibold text-foreground w-8 text-right">{pct}%</span>
    </div>
  );
}

interface SuggestionCardProps {
  suggestion: CopilotSuggestion;
  index: number;
  isPrimary: boolean;
  onCopy: (text: string) => void;
}
function SuggestionCard({ suggestion, index, isPrimary, onCopy }: SuggestionCardProps) {
  return (
    <div className={cn(
      "rounded-xl border p-3.5 transition-all",
      isPrimary
        ? "bg-indigo-50/70 border-indigo-200 shadow-sm"
        : "bg-white border-gray-100 hover:border-indigo-200"
    )}>
      {isPrimary && (
        <div className="flex items-center gap-1 mb-2 text-[10px] font-bold uppercase tracking-widest text-indigo-600">
          <CheckCircle2 className="w-3 h-3" /> 最优推荐
        </div>
      )}
      <p className="text-sm text-gray-800 leading-relaxed">{suggestion.content}</p>

      <div className="mt-2.5 space-y-1.5">
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="text-[10px] font-semibold border-indigo-200 text-indigo-700 bg-indigo-50/50">
            {suggestion.tactic}
          </Badge>
          <Button size="sm" variant="ghost" className="h-6 gap-1 text-xs text-gray-400 hover:text-indigo-600"
            onClick={() => onCopy(suggestion.content)}>
            <Copy className="w-3 h-3" /> 复制
          </Button>
        </div>

        <ConfidenceBar value={suggestion.confidence} label="置信度" />

        {suggestion.rationale && (
          <div className="flex items-start gap-1.5 pt-1 text-[11px] text-gray-500 leading-snug">
            <Brain className="w-3 h-3 mt-0.5 shrink-0 text-indigo-400" />
            <span>{suggestion.rationale}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------
// Chat Message Types
// -------------------------------------------------------------------

interface ChatMessage {
  role: 'customer' | 'ai_analysis';
  content: string;
  aiResponse?: CopilotResponse;
  timestamp: number;
}

// -------------------------------------------------------------------
// Main Component
// -------------------------------------------------------------------

export default function LiveAssist() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuthStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  const [deals, setDeals] = useState<Deal[]>([]);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingDeals, setLoadingDeals] = useState(true);

  // Latest AI analysis (displayed in right panel)
  const [latestAnalysis, setLatestAnalysis] = useState<CopilotResponse | null>(null);

  useEffect(() => { loadDeals(); }, []);
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function loadDeals() {
    try {
      const d = await dealService.list();
      const active = (Array.isArray(d) ? d : []).filter(x => !['closed_won', 'closed_lost'].includes(x.stage));
      setDeals(active);
      if (active.length > 0) setSelectedDeal(active[0] ?? null);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDeals(false);
    }
  }

  async function handleSend() {
    if (!inputText.trim() || loading) return;
    const text = inputText.trim();
    setInputText('');
    setLoading(true);

    setMessages(prev => [...prev, { role: 'customer', content: text, timestamp: Date.now() }]);

    try {
      const res = await dealService.copilotSuggest({
        deal_id: selectedDeal?.id,
        customer_message: text,
        mode: 'live',
        // @ts-ignore  – user_id for personalization
        user_id: user?.id ? String(user.id) : undefined,
      });

      setLatestAnalysis(res);
      setMessages(prev => [...prev, { role: 'ai_analysis', content: '', aiResponse: res, timestamp: Date.now() }]);
    } catch (e) {
      toast({ title: "获取建议失败", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  function copyText(text: string) {
    navigator.clipboard.writeText(text);
    toast({ title: "已复制到剪贴板" });
  }

  // -------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Zap className="w-6 h-6 text-amber-500" />
            实战辅助
            <Badge variant="outline" className="text-[10px] font-bold border-indigo-200 text-indigo-600 bg-indigo-50 ml-1">AI POWERED</Badge>
          </h1>
          <p className="text-gray-500 mt-0.5 text-sm">输入客户话语 · AI 三阶段分析 · 实时话术建议</p>
        </div>
        {!loadingDeals && deals.length > 0 && (
          <select
            className="border rounded-lg px-3 py-2 text-sm bg-white"
            value={selectedDeal?.id || ''}
            onChange={e => {
              const d = deals.find(x => x.id === parseInt(e.target.value));
              if (d) setSelectedDeal(d);
            }}
          >
            {deals.map(d => (
              <option key={d.id} value={d.id}>{d.customer_name} · {d.customer_company || ''}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Left: Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Card className="flex-1 border-0 shadow-sm flex flex-col overflow-hidden bg-gray-50/50">
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-400 py-16 text-center">
                  <Brain className="w-14 h-14 mb-4 opacity-20 text-indigo-400" />
                  <p className="text-sm font-medium mb-1">意图识别 · 阶段推断 · 策略生成</p>
                  <p className="text-xs opacity-60">输入客户刚说的话，AI 将在 &lt;2 秒内完成三阶段分析</p>
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div key={i}>
                    {/* Customer message */}
                    {msg.role === 'customer' && (
                      <div className="flex justify-end">
                        <div className="bg-gray-100 rounded-2xl rounded-tr-md px-4 py-2.5 max-w-[80%]">
                          <div className="text-[10px] text-gray-400 mb-1 font-semibold uppercase tracking-wide">客户说</div>
                          <div className="text-sm text-gray-900 font-medium">{msg.content}</div>
                        </div>
                      </div>
                    )}

                    {/* AI Analysis block */}
                    {msg.role === 'ai_analysis' && msg.aiResponse && (() => {
                      const res = msg.aiResponse;
                      const stageColor = STAGE_COLORS[res.detected_stage] || "bg-gray-100 text-gray-600 border-gray-200";
                      return (
                        <div className="space-y-3">
                          {/* Analysis Header */}
                          <div className="flex items-center gap-2 flex-wrap">
                            <div className="flex items-center gap-1.5 text-xs text-indigo-500 font-semibold">
                              <Sparkles className="w-3.5 h-3.5" />
                              AI 分析结果
                            </div>
                            <IntentBadge intentType={res.intent_type} confidence={res.intent_confidence} />
                            <Badge className={cn("text-[10px] border font-semibold", stageColor)}>
                              {STAGE_LABELS[res.detected_stage] || res.detected_stage}
                              <span className="opacity-60 ml-1">· {Math.round(res.stage_confidence * 100)}%</span>
                            </Badge>
                            {res.personalized && (
                              <Badge variant="outline" className="text-[10px] font-bold border-purple-200 text-purple-600 bg-purple-50">
                                ✦ 个性化
                              </Badge>
                            )}
                          </div>

                          {/* Intent Reasoning */}
                          {res.intent_reasoning && (
                            <div className="flex items-start gap-2 bg-white rounded-lg border border-gray-100 px-3 py-2 text-xs text-gray-500 leading-relaxed">
                              <Brain className="w-3.5 h-3.5 mt-0.5 shrink-0 text-indigo-400" />
                              <span>{res.intent_reasoning}</span>
                            </div>
                          )}

                          {/* Suggestions */}
                          <div className="space-y-2">
                            {res.suggestions?.map((s, j) => (
                              <SuggestionCard
                                key={j}
                                suggestion={s}
                                index={j}
                                isPrimary={j === 0}
                                onCopy={copyText}
                              />
                            ))}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ))
              )}
              <div ref={scrollRef} />
            </CardContent>

            {/* Input */}
            <div className="border-t bg-white p-3">
              <div className="flex gap-2">
                <Input
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                  placeholder="输入客户刚说的话..."
                  className="flex-1"
                  disabled={loading}
                />
                <Button
                  onClick={handleSend}
                  disabled={loading || !inputText.trim()}
                  className="bg-indigo-600 hover:bg-indigo-700 gap-1.5"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {!loading && "分析"}
                </Button>
              </div>
              <p className="text-[10px] text-gray-400 mt-1.5 flex items-center gap-1">
                <Brain className="w-3 h-3" />
                意图识别 → 阶段推断 → 策略生成 · 单次 LLM 调用 · &lt;2s
              </p>
            </div>
          </Card>
        </div>

        {/* Right: Context & Live Stats Panel */}
        <div className="w-72 shrink-0 hidden lg:flex flex-col gap-3">

          {/* Live AI Stats (shows latest analysis stats) */}
          {latestAnalysis && (
            <Card className="border-0 shadow-sm bg-gradient-to-b from-indigo-50/60 to-white">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-xs font-bold text-indigo-700 flex items-center gap-1.5 uppercase tracking-widest">
                  <Sparkles className="w-3.5 h-3.5" /> 实时分析仪表
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-3">
                <div>
                  <div className="text-[10px] text-gray-400 mb-1 font-semibold uppercase tracking-wide">检测意图</div>
                  <IntentBadge intentType={latestAnalysis.intent_type} confidence={latestAnalysis.intent_confidence} />
                </div>
                <div>
                  <div className="text-[10px] text-gray-400 mb-1 font-semibold uppercase tracking-wide">漏斗阶段置信度</div>
                  <ConfidenceBar value={latestAnalysis.stage_confidence} />
                </div>
                {latestAnalysis.personalized && (
                  <div className="flex items-center gap-2 bg-purple-50 rounded-lg border border-purple-100 px-2.5 py-2">
                    <User className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                    <span className="text-[11px] text-purple-700 font-semibold">已注入您的训练弱点档案</span>
                  </div>
                )}
                {latestAnalysis.methodology_gaps.length > 0 && (
                  <div>
                    <div className="text-[10px] text-gray-400 mb-1.5 font-semibold uppercase tracking-wide">方法论缺口</div>
                    <div className="flex flex-wrap gap-1">
                      {latestAnalysis.methodology_gaps.map(gap => (
                        <Badge key={gap} variant="outline" className="text-[10px] border-amber-200 text-amber-700 bg-amber-50">
                          {gap}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Deal Context */}
          {selectedDeal && (
            <Card className="border-0 shadow-sm flex-1">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-gray-700 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-indigo-500" /> 客户上下文
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <div className="font-semibold text-gray-900">{selectedDeal.customer_name}</div>
                  <div className="text-xs text-gray-400">{selectedDeal.customer_company} · {selectedDeal.customer_title}</div>
                </div>

                <div>
                  <div className="text-xs text-gray-500 mb-1">方法论完成度</div>
                  <ConfidenceBar value={selectedDeal.methodology_score / 100} />
                </div>

                {selectedDeal.methodology_state?.next_focus && (
                  <div className="bg-amber-50 rounded-lg border border-amber-100 p-3">
                    <div className="text-xs font-bold text-amber-700 mb-1 flex items-center gap-1">
                      <ChevronRight className="w-3 h-3" /> 下次重点
                    </div>
                    <div className="text-xs text-amber-600">{selectedDeal.methodology_state.next_focus}</div>
                  </div>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => navigate(`/student/battle-prep/${selectedDeal.id}`)}
                >
                  <Target className="w-3 h-3 mr-1" /> 查看完整战前准备
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
