import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';
import { CustomerCreate, CustomerPersona } from '@/services/customer.service';

interface CustomerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customer?: CustomerPersona;
  onSave: (data: CustomerCreate) => Promise<void>;
  loading?: boolean;
}

const avatarColors = [
  { value: 'from-blue-200 to-blue-400', label: '蓝色' },
  { value: 'from-purple-200 to-purple-400', label: '紫色' },
  { value: 'from-pink-200 to-pink-400', label: '粉色' },
  { value: 'from-orange-200 to-orange-400', label: '橙色' },
  { value: 'from-teal-200 to-teal-400', label: '青色' },
  { value: 'from-indigo-200 to-indigo-400', label: '靛青' },
];

export default function CustomerDialog({ open, onOpenChange, customer, onSave, loading }: CustomerDialogProps) {
  const [formData, setFormData] = useState<CustomerCreate>({
    name: '',
    age: 30,
    job: '',
    traits: [],
    description: '',
    avatar_color: 'from-blue-200 to-blue-400',
    scenario_id: 'default',
  });

  const [newTrait, setNewTrait] = useState('');

  useEffect(() => {
    if (customer) {
      setFormData({
        name: customer.name,
        age: customer.age,
        job: customer.job,
        traits: customer.traits,
        description: customer.description,
        avatar_color: customer.avatarColor,
        scenario_id: 'default',
      });
    } else {
      setFormData({
        name: '',
        age: 30,
        job: '',
        traits: [],
        description: '',
        avatar_color: 'from-blue-200 to-blue-400',
        scenario_id: 'default',
      });
    }
  }, [customer, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.job.trim()) return;

    const description = `${formData.age}岁 · ${formData.job} · ${formData.traits.join(' · ')}`;
    await onSave({ ...formData, description, scenario_id: formData.scenario_id || 'default' });
  };

  const addTrait = () => {
    if (newTrait.trim() && !formData.traits.includes(newTrait.trim())) {
      setFormData((prev) => ({ ...prev, traits: [...prev.traits, newTrait.trim()] }));
      setNewTrait('');
    }
  };

  const removeTrait = (trait: string) => {
    setFormData((prev) => ({ ...prev, traits: prev.traits.filter((t) => t !== trait) }));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTrait();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{customer ? '编辑客户' : '新建客户'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">客户名称 *</Label>
              <Input
                id="name"
                placeholder="例如：张先生"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="age">年龄 *</Label>
                <Input
                  id="age"
                  type="number"
                  min="18"
                  max="80"
                  value={formData.age}
                  onChange={(e) => setFormData((prev) => ({ ...prev, age: parseInt(e.target.value) || 30 }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="job">职业 *</Label>
                <Input
                  id="job"
                  placeholder="例如：企业高管"
                  value={formData.job}
                  onChange={(e) => setFormData((prev) => ({ ...prev, job: e.target.value }))}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>客户特征</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="添加特征，例如：有车、爱运动"
                  value={newTrait}
                  onChange={(e) => setNewTrait(e.target.value)}
                  onKeyPress={handleKeyPress}
                />
                <Button type="button" variant="outline" onClick={addTrait}>
                  添加
                </Button>
              </div>
              {formData.traits.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.traits.map((trait) => (
                    <Badge key={trait} variant="secondary" className="gap-1">
                      {trait}
                      <button
                        type="button"
                        onClick={() => removeTrait(trait)}
                        className="ml-1 hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label>头像颜色</Label>
              <div className="flex flex-wrap gap-2">
                {avatarColors.map((color) => (
                  <button
                    key={color.value}
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, avatar_color: color.value }))}
                    className={`w-10 h-10 rounded-full bg-gradient-to-br ${color.value} ring-2 ring-offset-2 ${
                      formData.avatar_color === color.value ? 'ring-purple-500' : 'ring-transparent'
                    } transition-all`}
                    title={color.label}
                  />
                ))}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? '保存中...' : customer ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
