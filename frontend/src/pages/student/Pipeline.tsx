import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Plus, Filter, Target, TrendingUp, DollarSign, ChevronRight } from "lucide-react";
import { dealService, Deal } from '@/services/deal.service';
import { useToast } from "@/hooks/use-toast";

const STAGES = [
  { value: "", label: "全部" },
  { value: "lead", label: "线索" },
  { value: "qualified", label: "机会" },
  { value: "proposal", label: "方案" },
  { value: "negotiation", label: "谈判" },
  { value: "closed_won", label: "成交" },
  { value: "closed_lost", label: "流失" },
];

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

const FUNNEL_COLORS: Record<string, string> = {
  lead: "bg-blue-400", qualified: "bg-cyan-400", proposal: "bg-amber-400",
  negotiation: "bg-purple-400", closed_won: "bg-green-400", closed_lost: "bg-red-400",
};

const FRAMEWORKS = [
  { value: "meddpicc", label: "MEDDPICC" },
  { value: "spin", label: "SPIN" },
  { value: "challenger", label: "Challenger" },
];

export default function Pipeline() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [stageFilter, setStageFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    customer_name: "", customer_company: "", customer_title: "",
    amount: "", methodology_framework: "meddpicc",
  });

  useEffect(() => { loadDeals(); }, []);

  async function loadDeals() {
    try {
      const d = await dealService.list();
      setDeals(Array.isArray(d) ? d : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!form.customer_name.trim()) return;
    setCreating(true);
    try {
      await dealService.create({
        customer_name: form.customer_name,
        customer_company: form.customer_company || undefined,
        customer_title: form.customer_title || undefined,
        amount: parseFloat(form.amount) || 0,
        methodology_framework: form.methodology_framework,
      });
      toast({ title: "商机已创建" });
      setShowCreate(false);
      setForm({ customer_name: "", customer_company: "", customer_title: "", amount: "", methodology_framework: "meddpicc" });
      loadDeals();
    } catch (e) {
      toast({ title: "创建失败", variant: "destructive" });
    } finally {
      setCreating(false);
    }
  }

  const filtered = stageFilter
    ? deals.filter(d => d.stage === stageFilter)
    : deals;

  const funnelStages = ["lead", "qualified", "proposal", "negotiation"];
  const funnelCounts = funnelStages.map(s => ({
    stage: s,
    count: deals.filter(d => d.stage === s).length,
    amount: deals.filter(d => d.stage === s).reduce((a, d) => a + (d.amount || 0), 0),
  }));
  const maxFunnel = Math.max(...funnelCounts.map(f => f.count), 1);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">我的漏斗</h1>
          <p className="text-gray-500 mt-1">管理商机，追踪每一笔交易</p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2 rounded-full bg-indigo-600 hover:bg-indigo-700">
          <Plus className="w-4 h-4" /> 新建商机
        </Button>
      </div>

      {/* Funnel Visualization */}
      <Card className="border-0 shadow-sm">
        <CardContent className="py-6">
          <div className="space-y-2">
            {funnelCounts.map((f, i) => {
              const widthPct = Math.max((f.count / maxFunnel) * 100, 12);
              return (
                <div key={f.stage} className="flex items-center gap-3">
                  <span className="w-12 text-xs text-gray-500 text-right">{STAGE_LABELS[f.stage]}</span>
                  <div className="flex-1 relative h-8">
                    <div
                      className={`h-full ${FUNNEL_COLORS[f.stage]} rounded-r-lg transition-all flex items-center px-3`}
                      style={{ width: `${widthPct}%` }}
                    >
                      <span className="text-white text-xs font-semibold">{f.count} 个</span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 w-20 text-right">¥{(f.amount / 10000).toFixed(1)}万</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {STAGES.map(s => (
          <Button
            key={s.value}
            variant={stageFilter === s.value ? "default" : "outline"}
            size="sm"
            className="rounded-full text-xs"
            onClick={() => setStageFilter(s.value)}
          >
            {s.label}
            {s.value && (
              <span className="ml-1 opacity-60">
                {deals.filter(d => d.stage === s.value).length}
              </span>
            )}
          </Button>
        ))}
      </div>

      {/* Deal List */}
      <Card className="border-0 shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-14 bg-gray-100 rounded animate-pulse" />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p>暂无商机</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => setShowCreate(true)}>
                创建第一个商机
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filtered.map(deal => (
                <div
                  key={deal.id}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/student/battle-prep/${deal.id}`)}
                >
                  <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-sm shrink-0">
                    {deal.customer_name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 text-sm">{deal.customer_name}</div>
                    <div className="text-xs text-gray-400 truncate">
                      {deal.customer_company || '—'} · {deal.customer_title || ''}
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-gray-700 w-24 text-right">
                    ¥{((deal.amount || 0) / 10000).toFixed(1)}万
                  </div>
                  <Badge className={`text-[10px] shrink-0 ${STAGE_COLORS[deal.stage] || 'bg-gray-100 text-gray-600'}`}>
                    {STAGE_LABELS[deal.stage] || deal.stage}
                  </Badge>
                  <div className="w-24 flex items-center gap-1 shrink-0">
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${deal.methodology_score || 0}%` }} />
                    </div>
                    <span className="text-[10px] text-gray-400 w-7 text-right">{Math.round(deal.methodology_score || 0)}%</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-300 shrink-0" />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>新建商机</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div>
              <Label>客户姓名 *</Label>
              <Input value={form.customer_name} onChange={e => setForm(f => ({ ...f, customer_name: e.target.value }))} placeholder="张总" />
            </div>
            <div>
              <Label>公司</Label>
              <Input value={form.customer_company} onChange={e => setForm(f => ({ ...f, customer_company: e.target.value }))} placeholder="科技有限公司" />
            </div>
            <div>
              <Label>职位</Label>
              <Input value={form.customer_title} onChange={e => setForm(f => ({ ...f, customer_title: e.target.value }))} placeholder="CTO" />
            </div>
            <div>
              <Label>预估金额 (元)</Label>
              <Input type="number" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} placeholder="100000" />
            </div>
            <div>
              <Label>销售方法论</Label>
              <select
                className="w-full border rounded-md px-3 py-2 text-sm"
                value={form.methodology_framework}
                onChange={e => setForm(f => ({ ...f, methodology_framework: e.target.value }))}
              >
                {FRAMEWORKS.map(fw => (
                  <option key={fw.value} value={fw.value}>{fw.label}</option>
                ))}
              </select>
            </div>
            <Button className="w-full" onClick={handleCreate} disabled={creating || !form.customer_name.trim()}>
              {creating ? "创建中..." : "创建商机"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
