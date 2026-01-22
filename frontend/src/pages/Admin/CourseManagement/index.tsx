import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PersonasTab } from "./PersonasTab";
import { CourseListTab } from "./CourseListTab";

export default function CourseManagementPage() {
  const [activeTab, setActiveTab] = useState("courses");

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">课程管理</h1>
        <p className="text-slate-500">管理培训课程和内容</p>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm min-h-[600px]">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="border-b border-slate-100 px-6 py-2">
            <TabsList className="grid w-[400px] grid-cols-2 bg-slate-100/50">
              <TabsTrigger value="courses">定制课程</TabsTrigger>
              <TabsTrigger value="personas">定制角色</TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            <TabsContent value="courses" className="m-0 focus-visible:outline-none">
              <CourseListTab />
            </TabsContent>
            <TabsContent value="personas" className="m-0 focus-visible:outline-none">
              <PersonasTab />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
