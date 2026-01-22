import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Edit, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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

// API Service (Mock for now, replace with real fetch)
const fetchCourses = async (): Promise<Course[]> => {
  // TODO: Replace with real API call
  // const res = await fetch('/api/v1/admin/courses');
  // return res.json();
  return [
    { id: "1", name: "基础销售技巧", description: "销售入门必修", difficulty_level: "beginner", is_active: true, product_category: "General", created_at: "2024-01-01" },
    { id: "2", name: "金融产品进阶", description: "理财产品销售话术", difficulty_level: "advanced", is_active: true, product_category: "Finance", created_at: "2024-01-02" },
  ];
};

export default function CoursesPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");

  const { data: courses, isLoading } = useQuery({
    queryKey: ["admin", "courses"],
    queryFn: fetchCourses,
  });

  const filteredCourses = courses?.filter(course => 
    course.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    course.product_category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">课程管理</h1>
        <Button>
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
                        <Button variant="ghost" size="icon">
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
