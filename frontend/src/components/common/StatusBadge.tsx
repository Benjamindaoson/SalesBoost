import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  let variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" = "secondary";
  let label = status;

  switch (status) {
    case "in_progress":
    case "进行中":
      variant = "info"; // We'll map 'info' to blue in badge.tsx if not present, or use custom class
      label = "进行中";
      break;
    case "completed":
    case "已结束":
    case "已完成":
      variant = "success";
      label = "已结束";
      break;
    case "not_started":
    case "未开始":
      variant = "secondary";
      label = "未开始";
      break;
    default:
      variant = "secondary";
  }

  // Custom colors based on image
  const getCustomClass = (s: string) => {
      if (s === 'in_progress' || s === '进行中') return "bg-blue-100 text-blue-600 hover:bg-blue-200";
      if (s === 'completed' || s === '已结束') return "bg-green-100 text-green-600 hover:bg-green-200";
      if (s === 'not_started' || s === '未开始') return "bg-gray-100 text-gray-500 hover:bg-gray-200";
      return "";
  }

  return (
    <Badge variant="outline" className={cn("border-none px-3 py-1 text-xs font-medium", getCustomClass(status), className)}>
      {label}
    </Badge>
  );
}
