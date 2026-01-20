import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  subLabel?: string;
  className?: string;
  iconClassName?: string;
  iconBgColor?: string;
}

export function StatCard({ label, value, icon: Icon, subLabel, className, iconClassName, iconBgColor }: StatCardProps) {
  return (
    <Card className={cn("border-none shadow-sm", className)}>
      <CardContent className="flex items-start justify-between p-6">
        <div>
           <div className="text-4xl font-bold text-gray-900 mb-2">{value}</div>
           <div className="text-sm text-gray-500 font-medium">{subLabel || label}</div>
        </div>
        {Icon && (
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-full", iconBgColor || "bg-gray-100")}>
            <Icon className={cn("h-5 w-5", iconClassName || "text-gray-600")} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
