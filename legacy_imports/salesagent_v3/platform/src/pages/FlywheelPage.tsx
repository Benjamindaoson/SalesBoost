import { useState, useEffect } from 'react';
import {
    BrainCircuit,
    Download,
    RefreshCw,
    CheckCircle2,
    AlertCircle
} from 'lucide-react';
import { api } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export function FlywheelPage() {
    const [pairs, setPairs] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadPairs();
    }, []);

    const loadPairs = async () => {
        setLoading(true);
        try {
            const data = await api.getPreferencePairs();
            setPairs(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const onExport = async () => {
        const blob = await api.exportDpo();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dpo_dataset_${new Date().toISOString().slice(0, 10)}.jsonl`;
        a.click();
    };

    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Data Flywheel</h2>
                    <p className="text-muted-foreground mt-1">Collecting preference pairs to align agent behavior via DPO & RL.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={loadPairs} disabled={loading}>
                        <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> Refresh
                    </Button>
                    <Button size="sm" onClick={onExport} className="bg-blue-600 hover:bg-blue-700">
                        <Download className="w-4 h-4 mr-2" /> Export DPO Dataset
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-sm font-medium">Recent Preference Pairs (Chosen vs Rejected)</CardTitle>
                        <div className="text-xs text-muted-foreground">Total pairs collected: {pairs.length}</div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {pairs.length === 0 && !loading && (
                                <div className="py-20 text-center opacity-40">No preference pairs collected yet.</div>
                            )}

                            {pairs.map((p) => (
                                <div key={p.id} className="border border-border rounded-xl overflow-hidden bg-muted/20">
                                    <div className="p-3 bg-secondary/30 border-b border-border flex justify-between items-center">
                                        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Session: {p.session_id.slice(0, 8)}...</span>
                                        <div className="flex gap-4">
                                            {Object.entries(p.reward_scores).filter(([k]) => k !== 'aggregate').map(([k, v]: any) => (
                                                <span key={k} className="text-[10px] text-muted-foreground">
                                                    {k}: <span className="text-primary font-medium">{(v * 100).toFixed(0)}%</span>
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2 text-[10px] font-bold text-green-500 uppercase">
                                                <CheckCircle2 size={12} /> Chosen Response
                                            </div>
                                            <div className="text-xs bg-green-500/5 border border-green-500/10 p-3 rounded-md min-h-[80px]">
                                                {p.chosen_response}
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2 text-[10px] font-bold text-red-500 uppercase">
                                                <AlertCircle size={12} /> Rejected Response
                                            </div>
                                            <div className="text-xs bg-red-500/5 border border-red-500/10 p-3 rounded-md min-h-[80px]">
                                                {p.rejected_response}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* APO Cycle Control */}
            <Card className="bg-blue-500/5 border-blue-500/20">
                <CardContent className="p-6 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/20 rounded-full">
                            <BrainCircuit className="text-blue-500" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-blue-400">APO Optimization Cycle</h4>
                            <p className="text-sm text-muted-foreground">Trigger the Adaptive Prompt Optimization loop to refine underperforming strategy prompts.</p>
                        </div>
                    </div>
                    <Button onClick={() => api.triggerApo()} className="bg-blue-600 hover:bg-blue-700">Trigger APO</Button>
                </CardContent>
            </Card>
        </div>
    );
}
