import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/common/ToastProvider";

type UserRecord = {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(`${API_BASE_URL}/admin/users`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error("加载用户失败");
        return (await response.json()) as UserRecord[];
      } catch (error) {
        console.error(error);
        pushToast("用户加载失败", "error");
        throw error;
      }
    },
  });

  const updateStatus = useMutation({
    mutationFn: async (user: UserRecord) => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(`${API_BASE_URL}/admin/users/${user.id}/status`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ is_active: !user.is_active }),
        });
        if (!response.ok) throw new Error("更新失败");
        return response.json();
      } catch (error) {
        console.error(error);
        pushToast("用户状态更新失败", "error");
        throw error;
      }
    },
    onSuccess: () => {
      pushToast("用户状态已更新", "success");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">学员账号管理</h1>
        <p className="text-sm text-slate-500">管理学员账号状态</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>账号列表</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-slate-500">加载中...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户名</TableHead>
                  <TableHead>邮箱</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users?.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.username}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell className="capitalize">{user.role}</TableCell>
                    <TableCell>
                      <label className="flex items-center gap-2 text-sm text-slate-600">
                        <input
                          type="checkbox"
                          checked={user.is_active}
                          onChange={() => updateStatus.mutate(user)}
                          disabled={updateStatus.isPending}
                        />
                        {user.is_active ? "正常" : "冻结"}
                      </label>
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {user.created_at ? new Date(user.created_at).toLocaleString() : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
