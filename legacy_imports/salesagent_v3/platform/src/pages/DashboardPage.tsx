import {
    Target,
    Zap,
    ShieldCheck,
    Database,
    ArrowUpRight,
    TrendingUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export function DashboardPage() {
    // Mock data for V3.1 Business Metrics
    const stats = [
        { label: 'Avg. Conversion Rate', value: '24.8%', change: '+3.2%', Icon: Target, color: 'text-blue-500', bg: 'bg-blue-500/10' },
        { label: 'Avg. Sales Cycle', value: '4.2 Days', change: '-1.5 Days', Icon: Zap, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
        { label: 'Reward Alignment', value: '92.4%', change: '+0.8%', Icon: ShieldCheck, color: 'text-green-500', bg: 'bg-green-500/10' },
        { label: 'DPO Active Pairs', value: '1,284', change: '+124', Icon: Database, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    ];

    return (
        <div className="p-6 space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Sales Operations Dashboard</h1>
                <p className="text-muted-foreground mt-1">Real-time business performance and agent alignment metrics.</p>
            </div>

            {/* Business KPI Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {stats.map((stat, i) => (
                    <Card key={i} className="border-none bg-card/50 backdrop-blur-sm shadow-lg overflow-hidden relative group">
                        <div className={`absolute top-0 right-0 w-24 h-24 -mr-8 -mt-8 rounded-full opacity-10 blur-2xl group-hover:scale-150 transition-transform duration-500 ${stat.bg}`} />
                        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                {stat.label}
                            </CardTitle>
                            <div className={`p-2 rounded-lg ${stat.bg} ${stat.color}`}>
                                <stat.Icon size={16} />
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stat.value}</div>
                            <div className="flex items-center gap-1 mt-1 text-xs font-medium text-green-500">
                                <ArrowUpRight size={12} />
                                <span>{stat.change}</span>
                                <span className="text-muted-foreground font-normal ml-1">vs last month</span>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
                {/* Sales Funnel Visualization */}
                <Card className="lg:col-span-4 border-muted/20 bg-card/30">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-blue-500" />
                            Conversion Funnel (V3.1 Ground Truth)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px] flex flex-col justify-end gap-2">
                        {/* Funnel visualization */}
                        {[
                            { stage: 'Discovery', count: 420, width: '100%', color: 'bg-blue-500/20' },
                            { stage: 'Proposal', count: 215, width: '51%', color: 'bg-blue-500/40' },
                            { stage: 'Negotiation', count: 86, width: '20%', color: 'bg-blue-500/60' },
                            { stage: 'Closed', count: 52, width: '12%', color: 'bg-blue-500/80' },
                        ].map((s) => (
                            <div key={s.stage} className="space-y-1">
                                <div className="flex justify-between text-xs font-medium">
                                    <span>{s.stage}</span>
                                    <span className="text-muted-foreground">{s.count} sessions</span>
                                </div>
                                <div className="h-6 w-full bg-secondary/20 rounded-sm overflow-hidden">
                                    <div className={`h-full ${s.color} transition-all duration-1000`} style={{ width: s.width }} />
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>

                {/* Reward Alignment Heatmap */}
                <Card className="lg:col-span-3 border-muted/20 bg-card/30">
                    <CardHeader>
                        <CardTitle>Reward Alignment</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {[
                            { label: 'Safety & Compliance', value: 99.8, color: 'bg-green-500' },
                            { label: 'Sales Task Progress', value: 84.2, color: 'bg-blue-500' },
                            { label: 'Tone & Soft Skills', value: 91.5, color: 'bg-purple-500' },
                            { label: 'RAG Accuracy', value: 88.0, color: 'bg-yellow-500' },
                        ].map(item => (
                            <div key={item.label} className="space-y-2">
                                <div className="flex justify-between text-xs">
                                    <span className="text-muted-foreground">{item.label}</span>
                                    <span className="font-bold">{item.value}%</span>
                                </div>
                                <div className="h-1.5 w-full bg-secondary/30 rounded-full overflow-hidden">
                                    <div className={`h-full ${item.color}`} style={{ width: `${item.value}%` }} />
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
