import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Search, 
  Folder, 
  ChevronRight, 
  ChevronDown, 
  Plus, 
  Star, 
  Camera, 
  Users, 
  Clock, 
  MoreHorizontal 
} from "lucide-react";
import { useState } from "react";
import { CreateCourseModal } from "./CreateCourseModal";

// Mock Directory Data
const directoryData = [
  { id: "all", name: "全部课程", active: true },
  { 
    id: "ops", 
    name: "运营联名高尔夫白金卡", 
    children: [
      { id: "new", name: "新客户开卡培训" },
      { id: "obj", name: "异议处理训练" },
      { id: "benefit", name: "权益推荐场景" },
    ]
  },
  { id: "visa", name: "Visa宝石币卡", children: [] },
  { id: "qq", name: "腾讯视频联名卡", children: [] },
];

// Mock Course Data
const courses = [
  {
    id: 1,
    title: "新客户开卡场景训练",
    desc: "针对新客户推荐白金卡的开卡场景...",
    people: 86,
    time: "今天 17:29",
    creator: "张经理",
    favorite: true,
  },
  {
    id: 2,
    title: "异议处理训练",
    desc: "客户对年费、权益等提出异议的应对...",
    people: 120,
    time: "今天 15:20",
    creator: "李经理",
    favorite: true,
  },
  {
    id: 3,
    title: "权益推荐场景",
    desc: "针对客户需求，精准推荐权益卡片...",
    people: 55,
    time: "昨天 23:16",
    creator: "王芳",
    favorite: true,
  },
];

export function CourseListTab() {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [expandedDirs, setExpandedDirs] = useState<string[]>(["ops"]);

  const toggleDir = (id: string) => {
    if (expandedDirs.includes(id)) {
      setExpandedDirs(expandedDirs.filter(d => d !== id));
    } else {
      setExpandedDirs([...expandedDirs, id]);
    }
  };

  return (
    <div className="flex gap-6 h-[600px]">
      {/* Left Directory */}
      <div className="w-64 border-r border-slate-100 pr-4 flex flex-col">
        <div className="mb-4">
          <h3 className="font-bold text-lg mb-4 text-slate-800">目录</h3>
          <div className="relative">
             <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
             <Input placeholder="搜索目录" className="pl-8 bg-slate-50 border-slate-200" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1">
          {directoryData.map((dir) => (
            <div key={dir.id}>
              <div 
                className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm font-medium transition-colors ${
                  dir.active ? "bg-purple-50 text-purple-700" : "text-slate-600 hover:bg-slate-50"
                }`}
                onClick={() => dir.children && toggleDir(dir.id)}
              >
                {dir.children && (
                  expandedDirs.includes(dir.id) ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />
                )}
                {!dir.children && <span className="w-4" />}
                <span>{dir.name}</span>
              </div>
              
              {dir.children && expandedDirs.includes(dir.id) && (
                <div className="ml-6 space-y-1 mt-1 border-l border-slate-100 pl-2">
                  {dir.children.map((child) => (
                    <div 
                      key={child.id}
                      className="px-3 py-2 rounded-lg cursor-pointer text-sm text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                    >
                      {child.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right Content */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex justify-between items-center mb-6">
          <div className="w-48">
            <Input placeholder="选择创建人" className="bg-white border-slate-200" />
          </div>
          <Button 
            className="bg-blue-600 hover:bg-blue-700 text-white gap-2"
            onClick={() => setCreateModalOpen(true)}
          >
            <Plus className="h-4 w-4" /> 新建课程
          </Button>
        </div>

        {/* Course Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 overflow-y-auto pb-4">
          {courses.map((course) => (
            <Card key={course.id} className="border-slate-200 hover:shadow-md transition-shadow group">
              <div className="relative h-32 bg-slate-100 rounded-t-xl flex items-center justify-center">
                <Camera className="h-12 w-12 text-slate-300" />
                {course.favorite && (
                  <div className="absolute top-3 right-3 bg-white p-1.5 rounded-full shadow-sm">
                    <Star className="h-4 w-4 text-yellow-400 fill-yellow-400" />
                  </div>
                )}
              </div>
              <CardContent className="p-4">
                <h3 className="font-bold text-slate-900 mb-2 line-clamp-1">{course.title}</h3>
                <p className="text-xs text-slate-500 mb-4 line-clamp-2 h-8">
                  {course.desc}
                </p>
                
                <div className="flex items-center justify-between text-xs text-slate-400 mb-4">
                  <div className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    <span>{course.people}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{course.time}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button className="flex-1 bg-blue-600 hover:bg-blue-700 text-white h-8 text-xs">
                    试用
                  </Button>
                  <Button variant="outline" className="flex-1 h-8 text-xs text-slate-600">
                    编辑
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <CreateCourseModal open={createModalOpen} onOpenChange={setCreateModalOpen} />
    </div>
  );
}
