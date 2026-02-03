import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  iconColor?: string;
  iconBgColor?: string;
  className?: string;
}

export function StatCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  iconColor = "text-primary",
  iconBgColor = "bg-primary/10",
  className 
}: StatCardProps) {
  return (
    <Card className={cn("border-none shadow-sm", className)}>
      <CardContent className="p-6 flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <div className="text-3xl font-bold">{value}</div>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <div className={cn("p-2 rounded-full", iconBgColor)}>
          <Icon className={cn("w-5 h-5", iconColor)} />
        </div>
      </CardContent>
    </Card>
  );
}
