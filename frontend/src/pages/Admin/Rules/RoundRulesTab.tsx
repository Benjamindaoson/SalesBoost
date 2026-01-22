import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pencil } from "lucide-react";

export function RoundRulesTab() {
  return (
    <div className="space-y-6">
      {/* Info Banner */}
      <div className="bg-[#F7F2FF] border border-purple-100 rounded-xl p-6 text-purple-900">
        <h3 className="font-bold mb-2">轮次规则说明</h3>
        <p className="text-sm opacity-90">
          配置一场对练的轮次限制、时长限制与结束条件。一场完整对练建议 8-15 个轮次，时长 15-25 分钟。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Round Limits Card */}
        <Card className="p-6 border-slate-200 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-lg text-slate-800">轮次限制</h3>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-blue-600">
              <Pencil className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="space-y-6">
            <div className="flex justify-between items-center pb-6 border-b border-slate-100">
              <div>
                <div className="font-bold text-slate-700 mb-1">最小轮次</div>
                <div className="text-xs text-slate-400">低于此轮次视为对话环节不完整</div>
              </div>
              <div className="bg-slate-100 px-3 py-1 rounded-md text-sm font-bold text-slate-700">8 轮</div>
            </div>

            <div className="flex justify-between items-center pb-6 border-b border-slate-100">
              <div>
                <div className="font-bold text-slate-700 mb-1">建议轮次</div>
                <div className="text-xs text-slate-400">正常完整对话范围</div>
              </div>
              <div className="bg-slate-100 px-3 py-1 rounded-md text-sm font-bold text-slate-700">10-15 轮</div>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <div className="font-bold text-slate-700 mb-1">最大轮次</div>
                <div className="text-xs text-slate-400">超过此轮次系统自动结束</div>
              </div>
              <div className="bg-slate-100 px-3 py-1 rounded-md text-sm font-bold text-slate-700">20 轮</div>
            </div>
          </div>
        </Card>

        {/* End Conditions Card */}
        <Card className="p-6 border-slate-200 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-lg text-slate-800">结束条件</h3>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-blue-600">
              <Pencil className="h-4 w-4" />
            </Button>
          </div>

          <div className="space-y-6">
            <div className="flex justify-between items-center pb-6 border-b border-slate-100">
              <div>
                <div className="font-bold text-slate-700 mb-1">成交成功</div>
                <div className="text-xs text-slate-400">销售员成功促成交易</div>
              </div>
              <Badge variant="secondary" className="bg-blue-50 text-blue-600 hover:bg-blue-100 border-blue-100">
                客户同意办卡
              </Badge>
            </div>

            <div className="flex justify-between items-center pb-6 border-b border-slate-100">
              <div>
                <div className="font-bold text-slate-700 mb-1">客户明确拒绝</div>
                <div className="text-xs text-slate-400">客户态度坚决，无法转可能</div>
              </div>
              <Badge variant="secondary" className="bg-blue-50 text-blue-600 hover:bg-blue-100 border-blue-100">
                多次拒绝
              </Badge>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <div className="font-bold text-slate-700 mb-1">达到轮次上限</div>
                <div className="text-xs text-slate-400">系统自动结束对话</div>
              </div>
              <Badge variant="secondary" className="bg-blue-50 text-blue-600 hover:bg-blue-100 border-blue-100">
                20 轮对话
              </Badge>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
