import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Edit2 } from "lucide-react";

const personas = [
  {
    id: 1,
    title: "年轻白领客户",
    tags: ["新客/潜客"],
    age: "25-35岁",
    income: "月收入8k-15k",
    consumption: ["高频次", "夜猫", "尝鲜"],
    traits: "理性、关注权益价值",
  },
  {
    id: 2,
    title: "高净值商务客户",
    tags: ["存量/高价值"],
    age: "35-50岁",
    income: "月收入30k+",
    consumption: ["机场贵宾", "酒店优惠", "高尔夫"],
    traits: "重视服务品质、时间敏感",
  },
  {
    id: 3,
    title: "学生群体客户",
    tags: ["新客/普卡"],
    age: "18-24岁",
    income: "无固定收入",
    consumption: ["日常消费", "线上购物"],
    traits: "价格敏感、关注优惠",
  },
  {
    id: 4,
    title: "家庭主理人",
    tags: ["存量/普卡"],
    age: "30-45岁",
    income: "月收入10k-20k",
    consumption: ["家庭消费", "子女教育"],
    traits: "稳健理性、关注实用性",
  },
];

export function PersonasTab() {
  return (
    <div className="space-y-6">
      <div>
        <Button className="bg-blue-600 hover:bg-blue-700 text-white gap-2">
          <Plus className="h-4 w-4" /> 新增模板
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {personas.map((persona) => (
          <Card key={persona.id} className="border-slate-200 hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
              <div className="space-y-1">
                <CardTitle className="text-lg font-bold text-slate-900">
                  {persona.title}
                </CardTitle>
                <div className="flex gap-2">
                  {persona.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="bg-blue-50 text-blue-600 hover:bg-blue-100">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
              <Button variant="ghost" size="icon" className="text-slate-400 hover:text-blue-600">
                <Edit2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="space-y-2 text-sm">
                <div className="flex">
                  <span className="w-20 text-slate-500">年龄：</span>
                  <span className="text-slate-900 font-medium">{persona.age}</span>
                </div>
                <div className="flex">
                  <span className="w-20 text-slate-500">收入：</span>
                  <span className="text-slate-900 font-medium">{persona.income}</span>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs text-slate-500 block">消费标签：</span>
                <div className="flex flex-wrap gap-2">
                  {persona.consumption.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-slate-600 border-slate-200 bg-slate-50">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-500 block">性格特点：</span>
                <p className="text-sm font-medium text-slate-900">{persona.traits}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
