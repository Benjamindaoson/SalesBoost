import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Edit2 } from "lucide-react";
import { WeightsTab } from "./WeightsTab";
import { StandardsTab } from "./StandardsTab";

const dimensions = [
  { id: 1, name: "完整性", weight: "20%", status: "已启用" },
  { id: 2, name: "相关性", weight: "20%", status: "已启用" },
  { id: 3, name: "正确性", weight: "25%", status: "已启用" },
  { id: 4, name: "逻辑表达能力", weight: "20%", status: "已启用" },
  { id: 5, name: "合规表现", weight: "15%", status: "已启用" },
];

export default function EvaluationSystemPage() {
  const [activeTab, setActiveTab] = useState("weights");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">评估体系管理</h1>
        <p className="text-slate-500">管理评估维度、评分标准、权重配置</p>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm min-h-[600px]">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="border-b border-slate-100 px-6 py-2">
            <TabsList className="grid w-[400px] grid-cols-3 bg-slate-100/50">
              <TabsTrigger value="dimensions">评估维度管理</TabsTrigger>
              <TabsTrigger value="scoring">评分标准管理</TabsTrigger>
              <TabsTrigger value="weights">权重配置</TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            <TabsContent value="dimensions" className="m-0 focus-visible:outline-none">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {dimensions.map((dim) => (
                  <Card key={dim.id} className="border-slate-200 hover:shadow-md transition-shadow">
                    <CardContent className="p-6 flex items-start justify-between">
                      <div className="flex gap-4">
                        <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center text-xl font-bold shadow-md">
                          {dim.id}
                        </div>
                        <div className="space-y-1">
                          <h3 className="font-bold text-lg text-slate-900">{dim.name}</h3>
                          <p className="text-sm text-slate-500">评估维度</p>
                          
                          <div className="flex items-center gap-6 mt-3">
                            <div className="space-y-1">
                              <span className="text-xs text-slate-400">当前权重</span>
                              <p className="font-bold text-blue-600">{dim.weight}</p>
                            </div>
                            <div className="space-y-1">
                              <span className="text-xs text-slate-400">启用状态</span>
                              <div>
                                <Badge variant="secondary" className="bg-green-50 text-green-600 hover:bg-green-100 border-green-200">
                                  {dim.status}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <Button variant="ghost" size="icon" className="text-slate-400 hover:text-blue-600">
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
            
            <TabsContent value="scoring" className="m-0 focus-visible:outline-none">
                <StandardsTab />
            </TabsContent>
            
            <TabsContent value="weights" className="m-0 focus-visible:outline-none">
                <WeightsTab />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
