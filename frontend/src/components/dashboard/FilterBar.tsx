import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search } from 'lucide-react';
import { cn } from "@/lib/utils";

interface FilterBarProps {
  currentFilter: string;
  onFilterChange: (filter: string) => void;
  onSearch: (query: string) => void;
}

const filters = [
  { id: 'all', label: '全部' },
  { id: 'pending', label: '未开始' },
  { id: 'in-progress', label: '进行中' },
  { id: 'completed', label: '已结束' },
];

export function FilterBar({ currentFilter, onFilterChange, onSearch }: FilterBarProps) {
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-4">
      <div className="relative w-full sm:w-[300px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input 
          placeholder="搜索课程名称、任务名称..." 
          className="pl-9 bg-gray-50 border-gray-200 rounded-full focus-visible:ring-primary"
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0">
        {filters.map((filter) => (
          <Button
            key={filter.id}
            variant={currentFilter === filter.id ? "default" : "outline"}
            size="sm"
            onClick={() => onFilterChange(filter.id)}
            className={cn(
              "rounded-full px-6 min-w-fit",
              currentFilter === filter.id 
                ? "bg-primary text-white hover:bg-primary/90 shadow-sm border-transparent" 
                : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50 hover:text-gray-900"
            )}
          >
            {filter.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
