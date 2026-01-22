import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Edit, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/common/ToastProvider";

// Types
interface Course {
  id: string;
  name: string;
  description: string;
  difficulty_level: string;
  is_active: boolean;
  product_category: string;
  created_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export default function CoursesPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [searchTerm, setSearchTerm] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newCourse, setNewCourse] = useState({
    name: "",
    description: "",
    difficulty_level: "beginner",
    is_active: true,
    product_category: "General",
  });

  const { data: courses, isLoading } = useQuery({
    queryKey: ["admin", "courses"],
    queryFn: async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(`${API_BASE_URL}/admin/courses`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error("加载课程失败");
        return (await response.json()) as Course[];
      } catch (error) {
        console.error(error);
        pushToast("课程加载失败，请稍后重试", "error");
        throw error;
      }
    },
  });

  const createCourse = useMutation({
    mutationFn: async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(`${API_BASE_URL}/admin/courses`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(newCourse),
        });
        if (!response.ok) throw new Error("创建课程失败");
        return response.json();
      } catch (error) {
        console.error(error);
        pushToast("课程创建失败，请检查输入", "error");
        throw error;
      }
    },
    onSuccess: () => {
      pushToast("课程创建成功", "success");
      setNewCourse({
        name: "",
        description: "",
        difficulty_level: "beginner",
        is_active: true,
        product_category: "General",
      });
      setShowCreateForm(false);
      queryClient.invalidateQueries({ queryKey: ["admin", "courses"] });
    },
  });

  const deleteCourse = useMutation({
    mutationFn: async (courseId: string) => {
      try {
        const token = localStorage.getItem("auth_token");
        const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}`, {
          method: "DELETE",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error("删除课程失败");
        return response;
      } catch (error) {
        console.error(error);
        pushToast("课程删除失败，请稍后重试", "error");
        throw error;
      }
    },
    onSuccess: () => {
      pushToast("课程已删除", "success");
      queryClient.invalidateQueries({ queryKey: ["admin", "courses"] });
    },
  });

  const filteredCourses = courses?.filter(course => 
    course.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    course.product_category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">课程管理</h1>
        <Button onClick={() => setShowCreateForm((prev) => !prev)}>
          <Plus className="mr-2 h-4 w-4" /> 新建课程
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-medium">课程列表</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
              <Input 
                placeholder="搜索课程..." 
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {showCreateForm && (
            <div className="mb-6 grid gap-4 rounded-lg border border-dashed border-slate-200 p-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  placeholder="课程名称"
                  value={newCourse.name}
                  onChange={(e) => setNewCourse((prev) => ({ ...prev, name: e.target.value }))}
                />
                <Input
                  placeholder="课程分类"
                  value={newCourse.product_category}
                  onChange={(e) => setNewCourse((prev) => ({ ...prev, product_category: e.target.value }))}
                />
              </div>
              <Input
                placeholder="课程描述"
                value={newCourse.description}
                onChange={(e) => setNewCourse((prev) => ({ ...prev, description: e.target.value }))}
              />
              <div className="flex flex-wrap items-center gap-4">
                <select
                  className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
                  value={newCourse.difficulty_level}
                  onChange={(e) => setNewCourse((prev) => ({ ...prev, difficulty_level: e.target.value }))}
                >
                  <option value="beginner">beginner</option>
                  <option value="intermediate">intermediate</option>
                  <option value="advanced">advanced</option>
                </select>
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={newCourse.is_active}
                    onChange={(e) => setNewCourse((prev) => ({ ...prev, is_active: e.target.checked }))}
                  />
                  立即发布
                </label>
                <Button
                  disabled={!newCourse.name.trim() || createCourse.isPending}
                  onClick={() => createCourse.mutate()}
                >
                  保存课程
                </Button>
              </div>
            </div>
          )}
          {isLoading ? (
            <div className="py-8 text-center text-slate-500">加载中...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>课程名称</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>难度</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCourses?.map((course) => (
                  <TableRow key={course.id}>
                    <TableCell className="font-medium">
                      <div>{course.name}</div>
                      <div className="text-xs text-slate-500 truncate max-w-[200px]">{course.description}</div>
                    </TableCell>
                    <TableCell>{course.product_category}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={
                        course.difficulty_level === "beginner" ? "bg-green-50 text-green-700 border-green-200" :
                        course.difficulty_level === "advanced" ? "bg-red-50 text-red-700 border-red-200" :
                        "bg-blue-50 text-blue-700 border-blue-200"
                      }>
                        {course.difficulty_level}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        course.is_active ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-800"
                      }`}>
                        {course.is_active ? "已发布" : "草稿"}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-500">{course.created_at}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="icon">
                          <Edit className="h-4 w-4 text-slate-500 hover:text-blue-600" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteCourse.mutate(course.id)}
                          disabled={deleteCourse.isPending}
                        >
                          <Trash2 className="h-4 w-4 text-slate-500 hover:text-red-600" />
                        </Button>
                      </div>
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
