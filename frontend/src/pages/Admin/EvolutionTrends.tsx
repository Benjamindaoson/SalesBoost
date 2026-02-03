import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Activity, ShieldAlert, Zap } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ScorePoint {
  timestamp: number;
  score: number;
}

interface ModelTrend {
  provider: string;
  model_name: string;
  current_score: number;
  negative_streak: number;
  total_calls: number;
  status: "ACTIVE" | "QUARANTINED";
  history: ScorePoint[];
}

interface IntentDistribution {
  [key: string]: number;
}

interface EvolutionResponse {
  trends: ModelTrend[];
  intent_distribution: IntentDistribution;
}

export default function EvolutionTrends() {
  const [data, setData] = useState<EvolutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchData = async () => {
    try {
      // Assuming API proxy is set up or CORS allows
      const response = await fetch("/api/v1/evolution-trends");
      if (!response.ok) {
        throw new Error("Failed to fetch trends");
      }
      const jsonData: EvolutionResponse = await response.json();
      setData(jsonData);
      setLoading(false);
    } catch (error) {
      console.error(error);
      // Don't toast on every poll error to avoid spam
      if (loading) {
        toast({
            title: "Error",
            description: "Failed to load evolution trends.",
            variant: "destructive"
        });
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="p-8">Loading evolution data...</div>;
  }

  if (!data) {
    return <div className="p-8">No data available.</div>;
  }

  // Transform history for Recharts
  // We need a common timeline or just individual charts. 
  // For simplicity, let's just plot the first active model or all of them on one chart if possible.
  // Actually, let's just show a chart for each model or a combined one.
  // Combined is tricky if timestamps don't align. Let's do individual small charts or one big one by mapping timestamps.
  
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Model Evolution</h2>
          <p className="text-muted-foreground">Real-time tracking of model performance and Darwinian selection.</p>
        </div>
        <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
                <Activity className="h-3 w-3" /> Live
            </Badge>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Models</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {data.trends.filter(m => m.status === "ACTIVE").length} / {data.trends.length}
            </div>
          </CardContent>
        </Card>
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Quarantined</CardTitle>
                <ShieldAlert className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold text-red-500">
                    {data.trends.filter(m => m.status === "QUARANTINED").length}
                </div>
            </CardContent>
        </Card>
      </div>

      {/* Main Charts Area */}
      <div className="grid gap-4 md:grid-cols-2">
        {data.trends.map((model) => (
            <Card key={`${model.provider}/${model.model_name}`} className={model.status === "QUARANTINED" ? "border-red-200 bg-red-50" : ""}>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-semibold">
                            {model.provider}/{model.model_name}
                        </CardTitle>
                        <Badge variant={model.status === "ACTIVE" ? "default" : "destructive"}>
                            {model.status}
                        </Badge>
                    </div>
                    <CardDescription>
                        Quality Score: {model.current_score.toFixed(2)} | Calls: {model.total_calls}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-[200px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={model.history.map(h => ({ ...h, time: new Date(h.timestamp * 1000).toLocaleTimeString() }))}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" hide />
                                <YAxis domain={[0, 10]} />
                                <Tooltip />
                                <Line type="monotone" dataKey="score" stroke="#8884d8" strokeWidth={2} dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>
        ))}
      </div>
      
      {/* Intent Distribution */}
      <Card>
          <CardHeader>
              <CardTitle>Traffic Intent Distribution</CardTitle>
          </CardHeader>
          <CardContent>
              <div className="space-y-2">
                  {Object.entries(data.intent_distribution).map(([intent, count]) => (
                      <div key={intent} className="flex items-center justify-between">
                          <span className="capitalize">{intent}</span>
                          <span className="font-bold">{count}</span>
                      </div>
                  ))}
              </div>
          </CardContent>
      </Card>
    </div>
  );
}
