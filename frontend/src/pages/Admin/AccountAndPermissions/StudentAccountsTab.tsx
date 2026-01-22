import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, Ban, CheckCircle, Lock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { adminService, User } from "@/services/api";

export default function StudentAccountsTab() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin", "users", "student"], // Filter cache key
    queryFn: async () => {
       const allUsers = await adminService.getUsers();
       return allUsers.filter(u => u.role === "student"); // Client-side filter
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      adminService.updateUserStatus(id, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const filteredUsers = users?.filter(user => 
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.full_name && user.full_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleToggleStatus = (user: User) => {
    if (confirm(`确认要${user.is_active ? '冻结' : '激活'}学员 ${user.username} 吗？`)) {
      toggleStatusMutation.mutate({ id: user.id, isActive: !user.is_active });
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium">学员列表</CardTitle>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="搜索学员姓名/账号..." 
              className="pl-8"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="py-8 text-center text-slate-500">加载中...</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>学员账号</TableHead>
                <TableHead>姓名</TableHead>
                <TableHead>部门</TableHead>
                <TableHead>训练次数</TableHead>
                <TableHead>最近训练</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers?.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.username}</TableCell>
                  <TableCell>{user.full_name || "-"}</TableCell>
                  <TableCell className="text-slate-500">销售一部</TableCell> {/* Mock data */}
                  <TableCell className="text-slate-500">12 次</TableCell> {/* Mock data */}
                  <TableCell className="text-slate-500">2024-12-10</TableCell> {/* Mock data */}
                  <TableCell>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      user.is_active ? "bg-green-100 text-green-800" : "bg-blue-100 text-blue-800"
                    }`}>
                      {user.is_active ? "正常" : "已冻结"}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                       <Button 
                        variant="ghost" 
                        size="icon"
                        className="text-slate-400"
                        title="重置密码 (Mock)"
                      >
                        <Lock className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant={user.is_active ? "ghost" : "ghost"} 
                        size="sm"
                        className={user.is_active ? "text-green-600 bg-green-50 hover:bg-green-100" : "text-blue-600 bg-blue-50 hover:bg-blue-100"}
                        onClick={() => handleToggleStatus(user)}
                        disabled={toggleStatusMutation.isPending}
                      >
                        {user.is_active ? "正常" : "已冻结"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {filteredUsers?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                    暂无数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
