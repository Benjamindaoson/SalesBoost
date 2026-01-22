import { Button } from "@/components/ui/button";

export function ProcessConfigTab() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-slate-400">
      <div className="text-center space-y-4">
        <h3 className="text-lg font-medium text-slate-900">销售流程配置</h3>
        <p>在此配置销售的标准SOP流程节点</p>
        <Button variant="outline">初始化默认流程</Button>
      </div>
    </div>
  );
}
