import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useState } from "react";

interface CreateCourseModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateCourseModal({ open, onOpenChange }: CreateCourseModalProps) {
  const [loading, setLoading] = useState(false);

  const handleCreate = () => {
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setLoading(false);
      onOpenChange(false);
    }, 1000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>新建课程</DialogTitle>
          <DialogDescription>
            创建新的培训课程，配置关联角色和销售流程。
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-6 py-4">
          <div className="grid gap-2">
            <Label htmlFor="name">课程名称 <span className="text-red-500">*</span></Label>
            <Input id="name" placeholder="请输入课程名称" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="directory">所属目录 <span className="text-red-500">*</span></Label>
            <Select defaultValue="all">
              <SelectTrigger>
                <SelectValue placeholder="选择目录" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部课程</SelectItem>
                <SelectItem value="new-client">新客户开卡培训</SelectItem>
                <SelectItem value="objection">异议处理训练</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="persona">选择对应角色</Label>
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="请选择客户角色" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="young">年轻白领客户</SelectItem>
                <SelectItem value="business">高净值商务客户</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label>销售流程配置</Label>
            <div className="grid grid-cols-2 gap-4 border rounded-lg p-4 bg-slate-50">
                <div className="flex items-center space-x-2">
                    <Checkbox id="stage1" defaultChecked />
                    <Label htmlFor="stage1" className="font-normal">开场破冰</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox id="stage2" defaultChecked />
                    <Label htmlFor="stage2" className="font-normal">产品介绍</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox id="stage3" defaultChecked />
                    <Label htmlFor="stage3" className="font-normal">客户探寻</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox id="stage4" defaultChecked />
                    <Label htmlFor="stage4" className="font-normal">权益推荐</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox id="stage5" defaultChecked />
                    <Label htmlFor="stage5" className="font-normal">异议处理</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox id="stage6" defaultChecked />
                    <Label htmlFor="stage6" className="font-normal">收尾促成</Label>
                </div>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleCreate} disabled={loading} className="bg-blue-600 hover:bg-blue-700">
            {loading ? "创建中..." : "创建"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
