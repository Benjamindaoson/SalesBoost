import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface EvaluationReportProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: any; // Using any for mock data simplicity
}

const mockData = {
  score: 85,
  improvement: 7,
  scenario: "新客户开卡·刘先生",
  dimensions: [
    { name: "开场破冰", score: 90, change: 8, status: "up" },
    { name: "产品介绍", score: 85, change: 5, status: "up" },
    { name: "客户洞察", score: 88, change: 10, status: "up" },
    { name: "异议处理", score: 78, change: -2, status: "down" },
    { name: "权益推荐", score: 88, change: 12, status: "up" },
    { name: "合规表达", score: 82, change: 3, status: "up" },
    { name: "收尾促成", score: 80, change: 0, status: "flat" },
    { name: "情绪安抚", score: 86, change: 6, status: "up" },
  ]
};

export function EvaluationReport({ open, onOpenChange, data = mockData }: EvaluationReportProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl p-0 overflow-hidden bg-slate-50 border-0">
        {/* Header Card */}
        <div className="bg-gradient-to-r from-purple-500 to-blue-600 p-8 text-white relative overflow-hidden">
            <div className="relative z-10 flex justify-between items-start">
                <div>
                    <h2 className="text-2xl font-medium mb-2 opacity-90">本次陪练综合评分</h2>
                    <div className="flex items-center gap-4 text-sm opacity-80">
                        <span>训练场景：{data.scenario}</span>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-8xl font-sans font-thin tracking-tighter leading-none mb-2">
                        {data.score}
                    </div>
                    <div className="flex items-center justify-end gap-1 text-yellow-300 font-medium">
                        <TrendingUp className="h-4 w-4" />
                        <span>较上次 +{data.improvement} 分</span>
                    </div>
                </div>
            </div>
            
            {/* Decorative circles */}
            <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-white opacity-5 blur-3xl"></div>
            <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-60 h-60 rounded-full bg-blue-400 opacity-20 blur-2xl"></div>
        </div>

        {/* Score Grid */}
        <div className="p-8">
            <h3 className="text-lg font-bold text-slate-800 mb-6">能力维度评分</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {data.dimensions.map((dim: any) => (
                    <div 
                        key={dim.name} 
                        className={`
                            p-5 rounded-xl border flex flex-col justify-between h-32 relative overflow-hidden transition-all hover:shadow-md
                            ${dim.status === 'down' ? 'bg-orange-50 border-orange-100' : 'bg-green-50/50 border-green-100'}
                        `}
                    >
                        <div className="flex justify-between items-start">
                            <span className="text-slate-700 font-medium text-lg">{dim.name}</span>
                        </div>
                        
                        <div className="flex justify-between items-end mt-4">
                             <div className={`text-sm font-bold flex items-center gap-1 
                                ${dim.status === 'up' ? 'text-green-600' : dim.status === 'down' ? 'text-orange-600' : 'text-slate-500'}
                             `}>
                                {dim.status === 'up' && <TrendingUp className="h-4 w-4" />}
                                {dim.status === 'down' && <TrendingDown className="h-4 w-4" />}
                                {dim.status === 'flat' && <Minus className="h-4 w-4" />}
                                
                                {dim.status === 'flat' ? '持平' : (dim.change > 0 ? `+${dim.change}` : dim.change)}
                             </div>
                             
                             <div className={`text-4xl font-light tracking-tight
                                ${dim.status === 'down' ? 'text-orange-500' : 'text-blue-600'}
                             `}>
                                {dim.score}
                             </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
