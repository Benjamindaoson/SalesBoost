import { CustomerPersona } from '@/types/business';
import { Button } from "@/components/ui/button";
import { User, Edit2, Trash2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CustomerCardProps {
  customer: CustomerPersona;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onRehearse?: (id: string) => void;
}

export function CustomerCard({ customer, onEdit, onDelete, onRehearse }: CustomerCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow duration-300 group">
      {/* Top Gradient Section with Avatar */}
      <div className={cn("h-32 bg-gradient-to-r relative flex items-center justify-center", customer.avatarColor || "from-blue-100 to-indigo-100")}>
        <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center shadow-inner">
          <User className="w-8 h-8 text-gray-400" />
        </div>
        {/* Creator badge */}
        <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-full text-xs text-gray-600 shadow-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
          {customer.creator}
        </div>
      </div>

      {/* Content Section */}
      <div className="p-5">
        <div className="mb-4">
          <h3 className="text-lg font-bold text-gray-900">{customer.name}</h3>
          <p className="text-sm text-gray-500 mt-1 leading-relaxed">
            {customer.age}岁 · {customer.job}
            {customer.traits.length > 0 && ` · ${customer.traits.join(' ')}`}
          </p>
        </div>

        {/* Stats Row */}
        <div className="flex items-center justify-end text-xs text-gray-400 mb-4 gap-1">
          <Clock className="w-3 h-3" />
          <span>{customer.rehearsalCount}次</span>
          <span className="mx-1">·</span>
          <span>{customer.lastRehearsalTime}</span>
        </div>

        {/* Action Bar */}
        <div className="flex items-center gap-3 mt-auto pt-3 border-t border-gray-50">
          <Button 
            className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-indigo-200 transition-all active:scale-95"
            onClick={() => onRehearse?.(customer.id)}
          >
            去预演
          </Button>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-9 w-9 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full" onClick={() => onEdit?.(customer.id)}>
              <Edit2 className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-9 w-9 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full" onClick={() => onDelete?.(customer.id)}>
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
