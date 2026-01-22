import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import AdminAccountsTab from "./AdminAccountsTab";
import StudentAccountsTab from "./StudentAccountsTab";
import RolePermissionsTab from "./RolePermissionsTab";
import { Shield, UserCog, Users } from "lucide-react";

export default function AccountAndPermissionsPage() {
  const [activeTab, setActiveTab] = useState("admin");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">账号与权限管理</h1>
          <p className="text-sm text-slate-500 mt-1">
            管理管理员账号、学员账号及角色权限配置
          </p>
        </div>
      </div>

      <Tabs defaultValue="admin" value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-white border">
          <TabsTrigger value="admin" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600">
            <Shield className="h-4 w-4 mr-2" />
            管理员账号管理
          </TabsTrigger>
          <TabsTrigger value="student" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600">
             <Users className="h-4 w-4 mr-2" />
             学员账号管理
          </TabsTrigger>
          <TabsTrigger value="role" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600">
            <UserCog className="h-4 w-4 mr-2" />
            角色权限配置
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="admin" className="space-y-4">
          <AdminAccountsTab />
        </TabsContent>
        
        <TabsContent value="student" className="space-y-4">
          <StudentAccountsTab />
        </TabsContent>

        <TabsContent value="role" className="space-y-4">
          <RolePermissionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
