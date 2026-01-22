import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RoundRulesTab } from "./RoundRulesTab";
import { ObjectionRulesTab } from "./ObjectionRulesTab";
import { ProcessConfigTab } from "./ProcessConfigTab";
import { GitBranch, MessageCircle, AlertCircle } from "lucide-react";

export default function RulesPage() {
  const [activeTab, setActiveTab] = useState("round_rules");

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">对练规则管理</h1>
        <p className="text-slate-500">配置销售流程、对练轮次规则与触发式异议规则</p>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm min-h-[600px]">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="border-b border-slate-100 px-6 py-2">
            <TabsList className="grid w-[600px] grid-cols-3 bg-slate-100/50">
              <TabsTrigger value="process" className="data-[state=active]:text-slate-900">
                <GitBranch className="h-4 w-4 mr-2" />
                销售流程配置
              </TabsTrigger>
              <TabsTrigger value="round_rules" className="data-[state=active]:text-blue-600">
                <MessageCircle className="h-4 w-4 mr-2" />
                对练轮次规则
              </TabsTrigger>
              <TabsTrigger value="objections" className="data-[state=active]:text-blue-600">
                <AlertCircle className="h-4 w-4 mr-2" />
                触发式异议规则
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            <TabsContent value="process" className="m-0 focus-visible:outline-none">
              <ProcessConfigTab />
            </TabsContent>
            <TabsContent value="round_rules" className="m-0 focus-visible:outline-none">
              <RoundRulesTab />
            </TabsContent>
            <TabsContent value="objections" className="m-0 focus-visible:outline-none">
              <ObjectionRulesTab />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
