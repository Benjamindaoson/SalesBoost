import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TaskCreate } from '@/services/task.service';

interface TaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: TaskCreate) => Promise<void>;
  loading?: boolean;
}

export default function TaskDialog({
  open,
  onOpenChange,
  onSave,
  loading = false
}: TaskDialogProps) {
  const [formData, setFormData] = useState<TaskCreate>({
    title: '',
    description: '',
    course_id: 1, // Default to 1 for now
    task_type: 'conversation',
    status: 'available',
    order: 1,
    points: 100,
    passing_score: 60,
    time_limit_minutes: 30,
    instructions: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>创建新任务</DialogTitle>
          <DialogDescription>
            填写任务详细信息以创建新的训练任务。
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="title">任务名称</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="例如：初次拜访模拟"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">任务类型</Label>
              <Select
                value={formData.task_type}
                onValueChange={(value: any) => setFormData({ ...formData, task_type: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="conversation">对话训练</SelectItem>
                  <SelectItem value="quiz">知识测验</SelectItem>
                  <SelectItem value="simulation">全流程模拟</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">任务描述</Label>
            <Input
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="简要描述任务目标..."
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="points">总分</Label>
              <Input
                id="points"
                type="number"
                value={formData.points}
                onChange={(e) => setFormData({ ...formData, points: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="passing_score">及格分</Label>
              <Input
                id="passing_score"
                type="number"
                value={formData.passing_score}
                onChange={(e) => setFormData({ ...formData, passing_score: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="time_limit">限时 (分钟)</Label>
              <Input
                id="time_limit"
                type="number"
                value={formData.time_limit_minutes}
                onChange={(e) => setFormData({ ...formData, time_limit_minutes: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="instructions">详细说明 / Prompt</Label>
            <Textarea
              id="instructions"
              value={formData.instructions}
              onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
              placeholder="输入给 AI 的系统提示词或给学员的操作指南..."
              className="h-32"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={loading} className="bg-purple-600 hover:bg-purple-700">
              {loading ? '创建中...' : '确认创建'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
