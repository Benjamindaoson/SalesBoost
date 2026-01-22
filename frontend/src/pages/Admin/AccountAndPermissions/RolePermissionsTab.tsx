import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Edit } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { adminService } from "@/services/api";

export default function RolePermissionsTab() {
  const { data: roles, isLoading } = useQuery({
    queryKey: ["admin", "roles"],
    queryFn: adminService.getRoles,
  });

  return (
    <div className="space-y-6">
      {roles?.map((role) => (
        <Card key={role.id}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg font-medium flex items-center gap-2">
                  {role.name}
                  {role.is_system && <Badge variant="outline" className="text-xs font-normal">系统内置</Badge>}
                </CardTitle>
                <p className="text-sm text-slate-500 mt-1">{role.description}</p>
              </div>
              <Button variant="outline" size="sm">
                <Edit className="mr-2 h-4 w-4" /> 编辑权限
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {role.permissions.includes("all") ? (
                <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-200">全部权限</Badge>
              ) : (
                <>
                  <Badge variant="secondary" className="bg-slate-100">账号与权限管理</Badge>
                  <Badge variant="secondary" className="bg-slate-100">知识库管理</Badge>
                  <Badge variant="secondary" className="bg-slate-100">模拟客户管理</Badge>
                  <Badge variant="secondary" className="bg-slate-100">评估体系管理</Badge>
                  <Badge variant="secondary" className="bg-slate-100">数据看板</Badge>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
