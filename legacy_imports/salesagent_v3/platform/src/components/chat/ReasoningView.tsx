import { Brain, Target, ShieldAlert, Zap } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export function ReasoningView() {
    const { currentReasoning, activeGuardEvents, latestRewardScores } = useAppStore();

    if (!currentReasoning) {
        return (
            <Card className="h-full bg-card flex items-center justify-center opacity-50">
                <div className="text-center space-y-4">
                    <Brain className="w-12 h-12 text-muted-foreground mx-auto animate-pulse" />
                    <p className="text-muted-foreground">Sales Agent Reasoning Engine Idle</p>
                </div>
            </Card>
        );
    }

    const { customer_signals, recommended_tactics, hidden_concerns } = currentReasoning;

    return (
        <Card className="h-full bg-card overflow-y-auto border-border">
            <CardHeader className="pb-3 border-b border-border bg-muted/30">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Brain className="w-4 h-4 text-blue-500" />
                    Reasoning Chain State
                </CardTitle>
            </CardHeader>

            <CardContent className="p-4 space-y-6">

                {/* Customer State Inference */}
                <section className="space-y-3">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-2">
                        <Target className="w-3 h-3" /> Customer Inference
                    </h4>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="bg-secondary/50 rounded-md p-3">
                            <span className="text-xs text-muted-foreground block mb-1">Objection</span>
                            <span className="text-sm font-medium">{customer_signals.objection_type}</span>
                        </div>
                        <div className="bg-secondary/50 rounded-md p-3">
                            <span className="text-xs text-muted-foreground block mb-1">Decision Stage</span>
                            <span className="text-sm font-medium">{customer_signals.decision_stage}</span>
                        </div>
                    </div>

                    <div className="space-y-2 pt-2">
                        <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Urgency ({Math.round(customer_signals.urgency * 100)}%)</span>
                            <span className="text-muted-foreground">Interest ({Math.round(customer_signals.interest_level * 100)}%)</span>
                        </div>
                        <div className="h-2 flex rounded-full overflow-hidden bg-secondary">
                            <div className="bg-orange-500" style={{ width: `${customer_signals.urgency * 100}%` }} />
                        </div>
                        <div className="h-2 flex rounded-full overflow-hidden bg-secondary">
                            <div className="bg-green-500" style={{ width: `${customer_signals.interest_level * 100}%` }} />
                        </div>
                    </div>
                </section>

                {/* Selected Tactics */}
                <section className="space-y-3 border-t border-border pt-4">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-2">
                        <Zap className="w-3 h-3" /> Agent Strategy
                    </h4>
                    <div className="space-y-2">
                        <div className="flex items-start gap-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 p-2 inset-0 rounded-md">
                            <span className="text-xs font-bold shrink-0 mt-0.5">PRI</span>
                            <span className="text-sm">{recommended_tactics.primary}</span>
                        </div>
                        <div className="flex items-start gap-2 bg-secondary p-2 rounded-md">
                            <span className="text-xs font-bold text-muted-foreground shrink-0 mt-0.5">SEC</span>
                            <span className="text-sm">{recommended_tactics.secondary}</span>
                        </div>
                    </div>

                    <div className="flex gap-2 flex-wrap pt-2">
                        <span className="text-xs bg-accent text-accent-foreground px-2 py-1 rounded-md border border-border">
                            Tone: {recommended_tactics.tone}
                        </span>
                    </div>
                </section>

                {/* Hidden Concerns */}
                {hidden_concerns.length > 0 && (
                    <section className="space-y-2 border-t border-border pt-4">
                        <h4 className="text-xs font-semibold uppercase text-muted-foreground">Diagnostic: Hidden Concerns</h4>
                        <ul className="list-disc list-inside space-y-1">
                            {hidden_concerns.map((c, i) => (
                                <li key={i} className="text-sm text-muted-foreground">{c}</li>
                            ))}
                        </ul>
                    </section>
                )}

                {/* Live Guard Stream */}
                {activeGuardEvents.length > 0 && (
                    <section className="space-y-2 border-t border-destructive/20 pt-4">
                        <h4 className="text-xs font-semibold uppercase text-destructive flex items-center gap-2">
                            <ShieldAlert className="w-3 h-3" /> Guard Interceptions
                        </h4>
                        <div className="space-y-2">
                            {activeGuardEvents.map((e, i) => (
                                <div key={i} className="bg-destructive/10 border border-destructive/20 rounded-md p-2 text-xs">
                                    <div className="font-semibold text-destructive mb-1">{e.risk_type}</div>
                                    <div className="line-through text-muted-foreground opacity-50 mb-1">{e.original}</div>
                                    <div className="text-green-500">{e.rewritten}</div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

            </CardContent>
        </Card>
    );
}
