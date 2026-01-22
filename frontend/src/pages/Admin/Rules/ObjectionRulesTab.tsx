import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, AlertCircle, Edit2 } from "lucide-react";

export function ObjectionRulesTab() {
  return (
    <div className="space-y-6">
      {/* Info Banner */}
      <div className="bg-[#FFF4EC] border border-orange-100 rounded-xl p-6 flex justify-between items-start">
        <div className="text-orange-900">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-5 w-5 text-orange-500" />
            <h3 className="font-bold">触发式异议说明</h3>
          </div>
          <p className="text-sm opacity-90 max-w-3xl">
            设定在特定对话场景下，异议类型。例如：销售员提到“年费”时，客户有30%概率提出“年费太贵”的异议。
          </p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700 text-white gap-2 shadow-sm">
          <Plus className="h-4 w-4" /> 新增规则
        </Button>
      </div>

      <div className="space-y-4">
        {/* Rule Block 1 */}
        <Card className="p-6 border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <div className="flex gap-4">
              <div className="h-10 w-10 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-lg">触发条件</h3>
                <p className="text-sm text-slate-500">销售员提及“年费”关键词</p>
              </div>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-blue-600">
              <Edit2 className="h-4 w-4" />
            </Button>
          </div>

          <div className="pl-14">
            <p className="text-sm text-slate-500 mb-3">可能的异议表述：</p>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-700 font-medium">"年费太贵了，能免吗？"</span>
                <span className="text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded">触发概率 30%</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-700 font-medium">"为什么要收年费？"</span>
                <span className="text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded">触发概率 20%</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-700 font-medium">"其他银行都免年费，你们也能免吗？"</span>
                <span className="text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded">触发概率 15%</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Rule Block 2 (Collapsed/Minimal) */}
        <Card className="p-6 border-slate-200 shadow-sm">
          <div className="flex justify-between items-start">
            <div className="flex gap-4">
              <div className="h-10 w-10 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-lg">触发条件</h3>
                <p className="text-sm text-slate-500">销售员介绍卡片权益</p>
              </div>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-blue-600">
              <Edit2 className="h-4 w-4" />
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
