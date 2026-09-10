import { useState, useEffect } from 'react';
import {
    FileText,
    History,
    Save,
    CheckCircle2,
    Layers,
    Code,
    ExternalLink
} from 'lucide-react';
import { api } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export function PromptsPage() {
    const [prompts, setPrompts] = useState<any[]>([]);
    const [selectedPrompt, setSelectedPrompt] = useState<any>(null);

    useEffect(() => {
        loadPrompts();
    }, []);

    const loadPrompts = async () => {
        try {
            const data = await api.getPrompts();
            setPrompts(data);
            if (data.length > 0 && !selectedPrompt) {
                setSelectedPrompt(data.find((p: any) => p.name === 'reasoning_system') || data[0]);
            }
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="p-8 space-y-8 h-full flex flex-col">
            <div className="flex justify-between items-end shrink-0">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Prompt Registry</h2>
                    <p className="text-muted-foreground mt-1">Version control, A/B testing, and regression analysis for agent prompts.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                        <History className="w-4 h-4 mr-2" /> Global Audit Log
                    </Button>
                    <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                        Deploy New Version
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 overflow-hidden">
                {/* Prompt Sidebar */}
                <Card className="lg:col-span-1 overflow-y-auto">
                    <CardHeader className="pb-2 border-b border-border">
                        <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground font-bold">Registers</CardTitle>
                    </CardHeader>
                    <CardContent className="p-2 space-y-1">
                        {prompts.filter(p => !p.name.includes('variant')).map((p) => (
                            <button
                                key={p.id}
                                onClick={() => setSelectedPrompt(p)}
                                className={`w-full text-left p-3 rounded-md transition-colors flex items-center justify-between group ${selectedPrompt?.name === p.name ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
                                    }`}
                            >
                                <div className="flex flex-col min-w-0">
                                    <span className="text-sm font-medium truncate">{p.name}</span>
                                    <span className={`text-[10px] ${selectedPrompt?.name === p.name ? 'text-blue-200' : 'text-muted-foreground'}`}>Version v{p.version}</span>
                                </div>
                                {p.status === 'active' && <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />}
                            </button>
                        ))}
                    </CardContent>
                </Card>

                {/* Editor / Details Area */}
                <div className="lg:col-span-3 flex flex-col gap-6 overflow-hidden">
                    {selectedPrompt ? (
                        <>
                            <Card className="flex-1 overflow-hidden flex flex-col">
                                <CardHeader className="flex flex-row items-center justify-between bg-muted/30 border-b border-border shrink-0">
                                    <div className="flex items-center gap-4">
                                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                                            <Code size={16} className="text-blue-500" /> {selectedPrompt.name}.jinja
                                        </CardTitle>
                                        <span className="text-xs bg-secondary px-2 py-0.5 rounded border border-border">v{selectedPrompt.version}</span>
                                        <span className="text-xs text-green-500 flex items-center gap-1 font-medium">
                                            <CheckCircle2 size={12} /> Live (100% Traffic)
                                        </span>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button variant="ghost" size="sm"><Layers size={14} className="mr-1.5" /> Diff</Button>
                                        <Button size="sm"><Save size={14} className="mr-1.5" /> Update Registry</Button>
                                    </div>
                                </CardHeader>
                                <CardContent className="p-0 flex-1 overflow-hidden">
                                    <textarea
                                        className="w-full h-full p-6 bg-transparent font-mono text-xs leading-relaxed outline-none resize-none text-muted-foreground focus:text-primary transition-colors scrollbar-thin scrollbar-thumb-primary/10"
                                        spellCheck={false}
                                        value={selectedPrompt.template}
                                        onChange={(e) => setSelectedPrompt({ ...selectedPrompt, template: e.target.value })}
                                    />
                                </CardContent>
                            </Card>

                            {/* Performance Context */}
                            <Card className="shrink-0 bg-blue-500/5 border-blue-500/10">
                                <CardContent className="p-4 flex items-center justify-between text-xs">
                                    <div className="flex gap-6">
                                        <div className="space-y-1">
                                            <span className="text-muted-foreground block">Avg. Reward</span>
                                            <span className="font-bold text-blue-400">{(selectedPrompt.avg_reward * 100).toFixed(1)}%</span>
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-muted-foreground block">Evaluations</span>
                                            <span className="font-bold">4,120</span>
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-muted-foreground block">Last Modified</span>
                                            <span className="font-bold">2 days ago</span>
                                        </div>
                                    </div>
                                    <Button variant="outline" size="sm" className="h-8">
                                        Run Performance Audit <ExternalLink size={12} className="ml-1.5" />
                                    </Button>
                                </CardContent>
                            </Card>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center opacity-30">
                            <FileText size={48} className="animate-pulse" />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
