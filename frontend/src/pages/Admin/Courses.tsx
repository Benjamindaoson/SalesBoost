import { useState, useEffect } from 'react';
import { 
  Plus, 
  Search, 
  MoreVertical, 
  Clock, 
  User, 
  Camera,
  ChevronRight,
  Eye,
  Edit2
} from 'lucide-react';
import { courseService, Course } from '@/services/course.service';
import { customerService } from '@/services/customer.service';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// 分类与角色来自 API

interface RoleItem {
  id: string;
  name: string;
  description: string;
  author: string;
  time: string;
}

export default function AdminCourses() {
  const [activeTab, setActiveTab] = useState("custom");
  const [selectedCategory, setSelectedCategory] = useState("全部课程");
  const [categories, setCategories] = useState<string[]>(["全部课程"]);
  const [courses, setCourses] = useState<Array<Course & { author?: string; time?: string }>>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [courseList, categoryList, customerList] = await Promise.all([
          courseService.list(),
          courseService.listCategories().catch(() => ["全部课程"]),
          customerService.getCustomers().catch(() => []),
        ]);
        setCourses(courseList.map((c) => ({
          ...c,
          author: '系统',
          time: (c as any).updated_at ? new Date((c as any).updated_at).toLocaleString('zh-CN') : '',
        })));
        setCategories(Array.isArray(categoryList) && categoryList.length > 0 ? categoryList : ["全部课程"]);
        setRoles(customerList.map((p) => ({
          id: p.id,
          name: p.name,
          description: p.description,
          author: p.creator,
          time: p.lastRehearsalTime || '',
        })));
      } catch {
        setCourses([]);
        setCategories(["全部课程"]);
        setRoles([]);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const filteredCourses = selectedCategory === "全部课程"
    ? courses
    : courses.filter((c) => c.category === selectedCategory || c.title.includes(selectedCategory));

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Page Header */}
      <div className="flex flex-col space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">课程管理</h1>
            <p className="text-sm text-gray-500 mt-1">管理培训课程和内容</p>
          </div>
        </div>

        {/* Tabs & Actions */}
        <div className="flex items-center justify-between border-b border-gray-200">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="flex items-center justify-between w-full mb-px">
              <TabsList className="bg-transparent p-0 h-auto space-x-6">
                <TabsTrigger 
                  value="catalog"
                  className="bg-transparent border-b-2 border-transparent px-2 py-3 rounded-none text-gray-500 data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-600 data-[state=active]:shadow-none font-medium"
                >
                  目录
                </TabsTrigger>
                <TabsTrigger 
                  value="custom"
                  className="bg-transparent border-b-2 border-transparent px-2 py-3 rounded-none text-gray-500 data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-600 data-[state=active]:shadow-none font-medium"
                >
                  定制课程
                </TabsTrigger>
                <TabsTrigger 
                  value="roles"
                  className="bg-transparent border-b-2 border-transparent px-2 py-3 rounded-none text-gray-500 data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-600 data-[state=active]:shadow-none font-medium"
                >
                  定制角色
                </TabsTrigger>
              </TabsList>
            </div>
          </Tabs>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 gap-6 overflow-hidden">
        {/* Left Sidebar (Only for Course Tabs) */}
        {activeTab !== 'roles' && (
          <div className="w-64 flex-shrink-0 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <span className="font-medium text-gray-700">目录</span>
              <MoreVertical className="w-4 h-4 text-gray-400 cursor-pointer" />
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {categories.map((cat, idx) => (
                <div 
                  key={idx}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-4 py-3 text-sm cursor-pointer flex items-center justify-between transition-colors ${
                    selectedCategory === cat 
                      ? 'bg-purple-50 text-purple-700 border-l-4 border-purple-600' 
                      : 'text-gray-600 hover:bg-gray-50 border-l-4 border-transparent'
                  }`}
                >
                  <span className="truncate">{cat}</span>
                  {selectedCategory === cat && <ChevronRight className="w-4 h-4" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Right Grid Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Filters Bar */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <Select defaultValue="creator">
                <SelectTrigger className="w-[140px] bg-white border-gray-200">
                  <SelectValue placeholder="请选择创建人" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="creator">请选择创建人</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
              
              {activeTab === 'roles' && (
                <Select defaultValue="type">
                  <SelectTrigger className="w-[140px] bg-white border-gray-200">
                    <SelectValue placeholder="课程类型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="type">课程类型</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>

            <Button className="bg-purple-600 hover:bg-purple-700 text-white gap-2">
              <Plus className="w-4 h-4" />
              {activeTab === 'roles' ? '定制角色' : '新建课程'}
            </Button>
          </div>

          {/* Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8">
            {loading && activeTab !== 'roles' ? (
              <div className="col-span-full py-12 text-center text-gray-500">加载中...</div>
            ) : activeTab === 'roles' ? (
              // Role Cards (from customers API)
              roles.map((role) => (
                <Card key={role.id} className="overflow-hidden border-gray-200 hover:shadow-lg transition-shadow duration-200 group">
                  <div className="h-32 bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center relative">
                    <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-purple-600">
                      <Camera className="w-6 h-6 text-gray-400" />
                    </div>
                  </div>
                  <CardContent className="p-5">
                    <h3 className="font-bold text-gray-900 text-lg mb-1">{role.name}</h3>
                    <p className="text-sm text-gray-500 line-clamp-2 h-10 mb-4">{role.description}</p>
                    
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        <span>{role.author}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{role.time}</span>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <Button variant="outline" className="flex-1 border-gray-200 text-gray-600 hover:text-purple-600 hover:border-purple-200">
                        <Edit2 className="w-4 h-4 mr-2" />
                        编辑
                      </Button>
                      <Button variant="outline" className="flex-1 border-gray-200 text-gray-600 hover:text-purple-600 hover:border-purple-200">
                        <Eye className="w-4 h-4 mr-2" />
                        详情
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              // Course Cards
              (loading ? [] : filteredCourses).map((course) => (
                <Card key={course.id} className="overflow-hidden border-gray-200 hover:shadow-lg transition-shadow duration-200 group">
                  <div className="h-32 bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center relative">
                    <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-purple-600">
                      <Camera className="w-6 h-6 text-gray-400" />
                    </div>
                  </div>
                  <CardContent className="p-5">
                    <h3 className="font-bold text-gray-900 text-lg mb-1">{course.title}</h3>
                    <p className="text-sm text-gray-500 line-clamp-2 h-10 mb-4">{course.description || ''}</p>
                    
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        <span>{course.author}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{course.time}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      <Button className="bg-indigo-500 hover:bg-indigo-600 text-white text-xs px-0 col-span-1">
                        去试用
                      </Button>
                      <Button variant="outline" className="border-gray-200 text-gray-600 text-xs px-0 col-span-1">
                        编辑
                      </Button>
                      <Button variant="outline" className="border-gray-200 text-gray-600 text-xs px-0 col-span-1">
                        预览
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
