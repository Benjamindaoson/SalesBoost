import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus } from "lucide-react";

export default function PersonasPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">人设管理</h1>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> 新建人设
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>客户画像列表</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">功能开发中...</p>
        </CardContent>
      </Card>
    </div>
  );
}
