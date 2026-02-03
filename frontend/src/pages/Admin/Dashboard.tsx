import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import { AlertCircle, DollarSign, Gauge, Users } from "lucide-react";
import api from "@/lib/api";

type CostTrendPoint = {
  date: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
};

type SkillAverages = {
  opening: number;
  discovery: number;
  closing: number;
};

type AnalyticsOverview = {
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  active_users_7d: number;
  total_practice_seconds_7d: number;
  competency_index: number;
  skill_averages: SkillAverages;
  cost_trend: CostTrendPoint[];
};

async function fetchAnalytics(): Promise<AnalyticsOverview> {
  const response = await api.get<AnalyticsOverview>("/admin/analytics");
  return response.data;
}

function formatCurrency(value: number) {
  return `$${value.toFixed(4)}`;
}

function formatHours(seconds: number) {
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function AdminDashboard() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-analytics"],
    queryFn: fetchAnalytics,
  });

  const radarData = useMemo(() => {
    if (!data) return [];
    return [
      { subject: "Opening", score: data.skill_averages.opening },
      { subject: "Discovery", score: data.skill_averages.discovery },
      { subject: "Closing", score: data.skill_averages.closing },
    ];
  }, [data]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 rounded bg-muted/60 animate-pulse" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <Card key={item}>
              <CardHeader className="space-y-2">
                <div className="h-4 w-32 rounded bg-muted/60 animate-pulse" />
                <div className="h-6 w-20 rounded bg-muted/60 animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-24 rounded bg-muted/60 animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((item) => (
            <Card key={item}>
              <CardHeader>
                <div className="h-4 w-40 rounded bg-muted/60 animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="h-[300px] rounded bg-muted/60 animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    const message = error instanceof Error ? error.message : "Failed to load analytics.";
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
        <Card className="border-destructive/40">
          <CardHeader className="flex flex-row items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <CardTitle className="text-base">Analytics unavailable</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">{message}</p>
            <Button variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const totalCost = formatCurrency(data.total_cost_usd);
  const competencyIndex = data.competency_index.toFixed(2);
  const totalPracticeHours = formatHours(data.total_practice_seconds_7d);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
      
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCost}</div>
            <p className="text-xs text-muted-foreground">
              Tokens: {data.total_input_tokens.toLocaleString()} in / {data.total_output_tokens.toLocaleString()} out
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users (7d)</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.active_users_7d.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Practice time: {totalPracticeHours}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Competency Index</CardTitle>
            <Gauge className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{competencyIndex}</div>
            <p className="text-xs text-muted-foreground">Scale 0-10 (Opening/Discovery/Closing)</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Cost Trend (7 days)</CardTitle>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.cost_trend}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(value) => format(new Date(value), "MM-dd")} />
                  <YAxis />
                  <Tooltip
                    formatter={(value: number | string) => formatCurrency(Number(value))}
                    labelFormatter={(label) => format(new Date(label), "MMM dd")}
                  />
                  <Bar dataKey="cost_usd" fill="#0f172a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Team Skill Radar</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" />
                  <PolarRadiusAxis domain={[0, 10]} />
                  <Radar dataKey="score" stroke="#0f172a" fill="#0f172a" fillOpacity={0.2} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-sm text-muted-foreground">
              <span>Opening: {data.skill_averages.opening.toFixed(2)}</span>
              <span>Discovery: {data.skill_averages.discovery.toFixed(2)}</span>
              <span>Closing: {data.skill_averages.closing.toFixed(2)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Alerts */}
      <Card>
        <CardHeader>
          <CardTitle>Training Alerts</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          No automated alerts configured yet. Connect evaluator thresholds to enable proactive flags.
        </CardContent>
      </Card>
    </div>
  );
}
