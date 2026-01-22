import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Upload } from "lucide-react";
import { useToast } from "@/components/common/ToastProvider";

export default function KnowledgePage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [sourceType, setSourceType] = useState("script");
  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

  const { data: assets, isLoading } = useQuery({
    queryKey: ["admin", "knowledge"],
    queryFn: async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(`${API_BASE_URL}/admin/knowledge`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error("加载知识库失败");
        return response.json();
      } catch (error) {
        console.error(error);
        pushToast("知识库加载失败", "error");
        throw error;
      }
    },
  });

  const handleUpload = async (file: File) => {
    try {
      const token = localStorage.getItem("auth_token");
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source_type", sourceType);

      const response = await fetch(`${API_BASE_URL}/admin/knowledge/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!response.ok) throw new Error("上传失败");
      pushToast("文档上传成功", "success");
      await response.json();
      queryClient.invalidateQueries({ queryKey: ["admin", "knowledge"] });
    } catch (error) {
      console.error(error);
      pushToast("文档上传失败，请重试", "error");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">知识库治理</h1>
        <div className="flex items-center gap-2">
          <select
            className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
          >
            <option value="script">话术</option>
            <option value="sop">SOP</option>
            <option value="objection">异议</option>
            <option value="faq">FAQ</option>
          </select>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                handleUpload(file);
                event.target.value = "";
              }
            }}
          />
          <Button onClick={() => fileInputRef.current?.click()}>
            <Upload className="mr-2 h-4 w-4" /> 上传文档
          </Button>
        </div>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>知识资产列表</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-slate-500">加载中...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>标题</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>向量同步</TableHead>
                  <TableHead>更新时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assets?.map((asset: any) => (
                  <TableRow key={asset.id}>
                    <TableCell className="font-medium">{asset.title}</TableCell>
                    <TableCell>{asset.source_type}</TableCell>
                    <TableCell>v{asset.active_version_number ?? "-"}</TableCell>
                    <TableCell>
                      <span className={asset.vector_status === "synced" ? "text-green-600" : "text-slate-500"}>
                        {asset.vector_status === "synced" ? "已同步" : "未启用"}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {asset.updated_at ? new Date(asset.updated_at).toLocaleString() : "-"}
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
