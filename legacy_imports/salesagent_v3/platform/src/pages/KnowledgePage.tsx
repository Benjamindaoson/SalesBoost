import React, { useState, useEffect } from 'react';
import {
    Database,
    Upload,
    Search,
    FileText,
    Play,
    Clock,
    Filter,
    CheckCircle2,
    AlertCircle
} from 'lucide-react';
import { api } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export function KnowledgePage() {
    const [chunks, setChunks] = useState<any[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [testQuery, setTestQuery] = useState('');
    const [retrievalResults, setRetrievalResults] = useState<any[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [isTesting, setIsTesting] = useState(false);

    useEffect(() => {
        loadChunks();
    }, []);

    const loadChunks = async () => {
        try {
            const data = await api.getKnowledgeChunks();
            setChunks(data);
        } catch (e) {
            console.error(e);
        }
    };

    const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setIsUploading(true);
        try {
            await api.uploadDocument(file);
            await loadChunks();
        } catch (e) {
            console.error(e);
        } finally {
            setIsUploading(false);
        }
    };

    const onTestRetrieval = async () => {
        if (!testQuery) return;
        setIsTesting(true);
        try {
            const data = await api.testRetrieval(testQuery);
            setRetrievalResults(data.results || []);
        } catch (e) {
            console.error(e);
        } finally {
            setIsTesting(false);
        }
    };

    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Knowledge Base</h2>
                    <p className="text-muted-foreground mt-1">Manage documents and test RAG retrieval performance (Dense + SelfRAG).</p>
                </div>
                <div>
                    <label className="cursor-pointer">
                        <input type="file" className="hidden" onChange={onUpload} disabled={isUploading} />
                        <div className={`flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium ${isUploading ? 'opacity-50' : ''}`}>
                            <Upload size={16} /> {isUploading ? 'Indexing...' : 'Upload Document'}
                        </div>
                    </label>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Retrieval Tester */}
                <Card className="lg:col-span-1 border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.05)]">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Search size={16} className="text-blue-500" /> Retrieval Sandbox
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex gap-2">
                            <Input
                                placeholder="Test query..."
                                value={testQuery}
                                onChange={(e) => setTestQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && onTestRetrieval()}
                            />
                            <Button size="icon" onClick={onTestRetrieval} disabled={isTesting}>
                                <Play size={16} className={isTesting ? 'animate-pulse' : ''} />
                            </Button>
                        </div>

                        <div className="space-y-3 min-h-[400px]">
                            {retrievalResults.length === 0 && !isTesting && (
                                <div className="py-20 text-center opacity-30 text-xs text-muted-foreground">Run a test query to see retrieval results</div>
                            )}
                            {retrievalResults.map((r, i) => (
                                <div key={i} className="bg-secondary/30 p-3 rounded-lg border border-border space-y-2">
                                    <div className="flex justify-between items-center text-[10px] uppercase font-bold text-muted-foreground">
                                        <span>Score: {r.rerank_score ? r.rerank_score.toFixed(3) : r.score.toFixed(3)}</span>
                                        <span className="flex items-center gap-1 text-blue-500">
                                            <Filter size={10} /> SELFRAG PASSED
                                        </span>
                                    </div>
                                    <p className="text-xs line-clamp-4 text-muted-foreground">{r.content}</p>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Knowledge Index */}
                <Card className="lg:col-span-2">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Database size={16} /> Indexed Chunks
                        </CardTitle>
                        <Input
                            placeholder="Search index..."
                            className="max-w-[200px] h-8 text-xs"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {chunks.map((c) => (
                                <div key={c.id} className="flex gap-4 p-4 rounded-lg bg-muted/20 border border-border hover:bg-muted/30 transition-colors">
                                    <div className="p-3 bg-secondary rounded-lg shrink-0 h-fit">
                                        <FileText className="text-muted-foreground" size={20} />
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 text-xs font-semibold">
                                            <span className="text-primary truncate max-w-[200px]">{c.document_name}</span>
                                            <span className="text-muted-foreground">Chunk #{c.chunk_index}</span>
                                        </div>
                                        <p className="text-sm text-muted-foreground leading-relaxed">{c.content.slice(0, 300)}...</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
