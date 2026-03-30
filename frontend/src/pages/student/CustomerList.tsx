import { useEffect, useState } from 'react';
import { 
  Search, 
  Plus, 
  Eye, 
  Pencil, 
  Trash2,
  Play,
  Smartphone
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { features } from '@/config/env';
import { CustomerPersona, customerService, getCustomersMock, CustomerCreate } from '@/services/customer.service';
import { useNavigate } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import CustomerDialog from '@/components/customer/CustomerDialog';
import CustomerViewDialog from '@/components/customer/CustomerViewDialog';

export default function StudentCustomers() {
  const [customers, setCustomers] = useState<CustomerPersona[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerPersona | null>(null);
  const [editingCustomer, setEditingCustomer] = useState<CustomerPersona | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleViewH5 = () => {
    window.open(window.location.href, '_blank', 'width=375,height=667');
  };

  const handleCreateCustomer = async (data: CustomerCreate) => {
    setSaving(true);
    try {
      if (features.useMockData) {
        const mockId = String(Date.now());
        const newCustomer: CustomerPersona = {
          ...data,
          id: mockId,
          creator: '当前用户',
          rehearsalCount: 0,
          lastRehearsalTime: '刚刚',
          avatarColor: data.avatar_color || 'from-blue-200 to-blue-400',
        };
        setCustomers((prev) => [...prev, newCustomer]);
        toast({ title: '创建成功', description: `客户 ${data.name} 已创建` });
        setCreateDialogOpen(false);
      } else {
        const newCustomer = await customerService.createCustomer(data);
        setCustomers((prev) => [...prev, newCustomer]);
        toast({ title: '创建成功', description: `客户 ${data.name} 已创建` });
        setCreateDialogOpen(false);
      }
    } catch (error) {
      toast({
        title: '创建失败',
        description: '无法创建客户，请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleViewCustomer = (customer: CustomerPersona) => {
    setSelectedCustomer(customer);
    setViewDialogOpen(true);
  };

  const handleEditCustomer = (customer: CustomerPersona) => {
    setEditingCustomer(customer);
  };

  const handleUpdateCustomer = async (data: CustomerCreate) => {
    setSaving(true);
    try {
      const updated = await customerService.updateCustomer(editingCustomer!.id, data);
      setCustomers((prev) => prev.map((c) => (c.id === editingCustomer?.id ? { ...updated, ...c, ...data } : c)));
      toast({
        title: '更新成功',
        description: `客户 ${data.name} 信息已更新`,
      });
      setEditingCustomer(null);
    } catch (error) {
      toast({
        title: '更新失败',
        description: '无法更新客户信息，请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCustomer = async (customer: CustomerPersona) => {
    if (!confirm(`确定要删除客户 ${customer.name} 吗？`)) return;

    try {
      await customerService.deleteCustomer(customer.id);
      setCustomers((prev) => prev.filter((c) => c.id !== customer.id));
      toast({
        title: '删除成功',
        description: `客户 ${customer.name} 已删除`,
      });
    } catch (error) {
      toast({
        title: '删除失败',
        description: '无法删除客户，请稍后重试',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    const fetchCustomers = async () => {
      setLoading(true);
      try {
        if (features.useMockData) {
          setCustomers(await getCustomersMock());
        } else {
          setCustomers(await customerService.getCustomers());
        }
      } catch (error) {
        if (!features.useMockData) {
          setCustomers([]);
          toast({
            title: '加载失败',
            description: '无法加载客户列表，请检查网络连接',
            variant: 'destructive',
          });
        } else {
          setCustomers(await getCustomersMock());
        }
      } finally {
        setLoading(false);
      }
    };
    fetchCustomers();
  }, []);

  const filteredCustomers = customers.filter((c) =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.job.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">客户预演</h1>
          <p className="text-sm text-gray-500 mt-1">创建个性化客户画像</p>
        </div>
        <Button 
          size="sm" 
          className="rounded-full gap-2 bg-purple-50 text-purple-600 hover:bg-purple-100 border border-purple-100 shadow-none"
          onClick={handleViewH5}
        >
          <Smartphone className="w-4 h-4 mr-2" />
          查看 H5 版本
        </Button>
      </div>

      {/* Main Content */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
             <h2 className="text-lg font-semibold text-gray-900">客户预演</h2>
             <p className="text-xs text-gray-500 mt-0.5">选择和创建客户角色进行销售模拟</p>
          </div>
          <Button 
            className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg shadow-md shadow-purple-200"
            onClick={() => setCreateDialogOpen(true)}
          >
            <Plus className="w-4 h-4 mr-2" />
            新建预演角色
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="搜索客户名称或职业..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 max-w-md"
          />
        </div>

        {/* Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-500">加载中...</div>
          </div>
        ) : filteredCustomers.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-500 text-center">
              <p className="text-lg font-medium mb-2">没有找到客户</p>
              <p className="text-sm">点击"新建预演角色"创建您的第一个客户</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCustomers.map((customer) => (
            <Card key={customer.id} className="overflow-hidden border-gray-100 hover:shadow-lg transition-shadow duration-200 group">
              {/* Gradient Header */}
              <div className={`h-24 bg-gradient-to-r ${customer.avatarColor || 'from-purple-200 to-blue-200'} opacity-30 relative`}>
              </div>
              
              <CardContent className="p-0 relative">
                 {/* Avatar */}
                 <div className="absolute -top-10 left-1/2 -translate-x-1/2">
                    <div className="w-20 h-20 rounded-full bg-white p-1.5 shadow-sm">
                      <div className={`w-full h-full rounded-full bg-gradient-to-br ${customer.avatarColor || 'from-purple-100 to-blue-100'} flex items-center justify-center`}>
                        <span className="text-2xl font-bold text-gray-700 opacity-50">
                          {customer.name.charAt(0)}
                        </span>
                      </div>
                    </div>
                 </div>

                 {/* Content */}
                 <div className="mt-12 px-6 pb-6 text-center">
                   <h3 className="font-bold text-gray-900 text-lg">{customer.name}</h3>
                   <div className="text-xs text-gray-500 mt-2 line-clamp-2 h-8 px-4 leading-relaxed">
                     {customer.description}
                   </div>
                   
                   <div className="flex items-center justify-center gap-2 mt-4 text-xs text-gray-400">
                     <span className="bg-gray-50 px-2 py-1 rounded">关联人: A. {customer.creator}</span>
                   </div>

                   {/* Footer Actions */}
                   <div className="mt-6 flex items-center justify-between pt-4 border-t border-gray-50">
                     <Button 
                        className="bg-purple-600 hover:bg-purple-700 text-white text-xs h-8 px-4 rounded-full flex-1 mr-3 shadow-sm shadow-purple-200"
                        onClick={() => navigate('/student/training')}
                      >
                       <Play className="w-3 h-3 mr-1 fill-current" /> 去预演
                     </Button>
                     <div className="flex gap-1">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                          onClick={() => handleViewCustomer(customer)}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                          onClick={() => handleEditCustomer(customer)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-gray-400 hover:text-red-500 rounded-full hover:bg-red-50"
                          onClick={() => handleDeleteCustomer(customer)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                     </div>
                   </div>

                   <div className="mt-3 flex items-center justify-end">
                      <span className="text-[10px] text-gray-300 flex items-center">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-300 mr-1"></span>
                        {customer.lastRehearsalTime}
                      </span>
                   </div>
                 </div>
              </CardContent>
            </Card>
          ))}
          </div>
        )}
      </div>

      {/* Dialogs */}
      <CustomerDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSave={handleCreateCustomer}
        loading={saving}
      />
      <CustomerDialog
        open={!!editingCustomer}
        onOpenChange={(open) => !open && setEditingCustomer(null)}
        customer={editingCustomer || undefined}
        onSave={handleUpdateCustomer}
        loading={saving}
      />
      <CustomerViewDialog
        open={viewDialogOpen}
        onOpenChange={setViewDialogOpen}
        customer={selectedCustomer}
        onEdit={handleEditCustomer}
        onDelete={handleDeleteCustomer}
      />
    </div>
  );
}
