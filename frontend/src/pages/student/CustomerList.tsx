import { useEffect, useState } from 'react';
import { Plus, Search, Edit2, Trash2, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getCustomers } from '@/services/mockData';
import { CustomerPersona } from '@/types/business';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

export default function CustomerList() {
  const [customers, setCustomers] = useState<CustomerPersona[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getCustomers();
        setCustomers(data);
      } catch (error) {
        console.error('Failed to fetch customers', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const filteredCustomers = customers.filter(customer => 
    customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    customer.job.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">客户预演</h1>
          <p className="text-gray-500 mt-1">创建个性化客户画像</p>
        </div>
        <div className="flex items-center gap-3">
          <Button className="bg-purple-600 hover:bg-purple-700 text-white rounded-full px-6 shadow-lg shadow-purple-200">
            <Plus className="w-4 h-4 mr-2" />
            新建预演角色
          </Button>
        </div>
      </div>

      {/* Sub-header / Filter */}
      <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-sm text-gray-500">
            <span className="font-bold text-gray-900">客户预演</span>
            <span className="mx-2">|</span>
            选择或创建客户角色进行情境演练
          </div>
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input 
              placeholder="搜索姓名、职业..." 
              className="pl-9 bg-gray-50 border-gray-200 focus:bg-white transition-all rounded-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Customer Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-64 w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCustomers.map((customer) => (
            <div 
              key={customer.id} 
              className="group relative bg-white rounded-xl overflow-hidden border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300"
            >
              {/* Gradient Background Top */}
              <div className={cn("h-32 bg-gradient-to-r opacity-10 group-hover:opacity-20 transition-opacity", customer.avatarColor || 'from-purple-400 to-indigo-500')}></div>
              
              {/* Avatar */}
              <div className="absolute top-16 left-1/2 -translate-x-1/2">
                 <div className="w-20 h-20 rounded-full bg-white p-1 shadow-lg">
                   <div className={cn("w-full h-full rounded-full bg-gradient-to-br flex items-center justify-center text-white text-2xl font-bold", customer.avatarColor || 'from-purple-500 to-indigo-600')}>
                     {customer.name.charAt(0)}
                   </div>
                 </div>
              </div>

              {/* Content */}
              <div className="pt-12 pb-6 px-6 text-center">
                <h3 className="text-lg font-bold text-gray-900">{customer.name}</h3>
                <p className="text-sm text-gray-500 mt-1 mb-3">{customer.description}</p>
                
                {/* Creator & Time Info */}
                <div className="flex items-center justify-between text-xs text-gray-400 mt-4 px-2">
                  <div className="flex items-center gap-1">
                    <span className="w-4 h-4 rounded-full bg-gray-100 flex items-center justify-center text-[10px] font-bold text-gray-600">
                      {customer.creator?.charAt(0) || 'A'}
                    </span>
                    <span>{customer.creator}</span>
                  </div>
                  <div className="flex flex-col items-end">
                    {customer.rehearsalCount > 0 && (
                      <span className="text-purple-600 font-medium mb-0.5">{customer.rehearsalCount}次</span>
                    )}
                    <span>{customer.lastRehearsalTime}</span>
                  </div>
                </div>
              </div>

              {/* Action Bar */}
              <div className="border-t border-gray-50 p-4 flex items-center justify-between gap-3 bg-gray-50/50">
                <Button className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-200 rounded-full h-9">
                  去预演
                </Button>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-gray-400 hover:text-gray-900 hover:bg-white">
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-gray-400 hover:text-red-600 hover:bg-white">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Pagination (Visual Only) */}
      {!loading && (
        <div className="flex justify-between items-center text-sm text-gray-500 pt-4">
          <div>共 {filteredCustomers.length} 条</div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled>上一页</Button>
            <Button variant="default" size="sm" className="bg-purple-600">1</Button>
            <Button variant="outline" size="sm">下一页</Button>
            <span className="ml-2 border rounded px-2 py-1 bg-white">20条/页</span>
          </div>
        </div>
      )}
    </div>
  );
}
