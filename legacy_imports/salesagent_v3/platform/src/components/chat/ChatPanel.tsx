import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, AlertTriangle } from 'lucide-react';
import { useSSE } from '@/hooks/useSSE';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { FSMTracker } from './FSMTracker';
import { ReasoningView } from './ReasoningView';

export function ChatPanel() {
    const { messages, isTyping, isWaitingApproval, sendMessage, approveMessage, stopGeneration } = useSSE();
    const [input, setInput] = useState('');
    const [overrideText, setOverrideText] = useState('');
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const onSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isTyping || isWaitingApproval) return;
        sendMessage(input);
        setInput('');
    };

    const handleApprove = () => {
        approveMessage(overrideText || null);
        setOverrideText('');
    };

    return (
        <div className="flex h-full w-full overflow-hidden flex-col lg:flex-row bg-[#0D0D12]">

            {/* Central Chat View */}
            <div className="flex-1 flex flex-col min-w-0 border-r border-border">

                {/* Top FSM Progress Bar */}
                <FSMTracker />

                {/* Message Log */}
                <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
                    {messages.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center text-center opacity-50 space-y-4">
                            <Bot className="w-16 h-16 text-muted-foreground" />
                            <div className="text-xl font-medium">Start the Sales Simulation</div>
                            <p className="max-w-md text-sm text-muted-foreground">
                                Type an objection or question to test the Agent's reasoning, defense, and closing abilities.
                            </p>
                        </div>
                    )}

                    {messages.map((m) => (
                        <div key={m.id} className={`flex gap-4 max-w-3xl ${m.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
                            <div className={`w-8 h-8 rounded-full flex shrink-0 items-center justify-center mt-1 ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-primary/20 text-primary border border-primary/30'
                                }`}>
                                {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>
                            <div className={`flex flex-col gap-1 ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                                <div className="text-xs text-muted-foreground tracking-wide font-medium flex items-center gap-2">
                                    {m.role === 'user' ? 'You' : 'SalesAgent'}
                                    {m.role === 'assistant' && (m.isStreaming || isWaitingApproval) && (
                                        <span className="flex items-center gap-1 text-[10px] text-blue-500 bg-blue-500/10 px-1.5 py-0.5 rounded">
                                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                            {isWaitingApproval ? 'WAITING APPROVAL' : 'REASONING & STREAMING'}
                                        </span>
                                    )}
                                </div>
                                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${m.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-tr-sm shadow-md'
                                    : 'bg-card border border-border text-card-foreground rounded-tl-sm shadow-sm'
                                    }`}>
                                    {m.content}
                                    {m.isStreaming && !m.content && (
                                        <span className="animate-pulse text-muted-foreground shrink-0">· · ·</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* HITL Intervention Overlay */}
                    {isWaitingApproval && (
                        <div className="mx-auto max-w-2xl bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-6 space-y-4 animate-in fade-in slide-in-from-bottom-4">
                            <div className="flex items-center gap-3 text-yellow-500">
                                <AlertTriangle className="w-5 h-5" />
                                <span className="font-semibold text-sm uppercase tracking-wider">Manager Intervention Required</span>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                AI has paused at a high-stakes stage (<span className="text-foreground font-medium">Proposal/Closing</span>).
                                Review the reasoning on the right and choose to approve the draft or provide a manual override.
                            </p>
                            <div className="space-y-3">
                                <textarea
                                    className="w-full bg-background border border-border rounded-lg p-3 text-sm focus:ring-1 focus:ring-yellow-500/50 outline-none"
                                    placeholder="Enter manual override text here... (Optional)"
                                    value={overrideText}
                                    onChange={(e) => setOverrideText(e.target.value)}
                                    rows={3}
                                />
                                <div className="flex gap-3">
                                    <Button
                                        onClick={handleApprove}
                                        className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white"
                                    >
                                        {overrideText ? 'Apply Override & Send' : 'Approve & Send Draft'}
                                    </Button>
                                    <Button
                                        variant="outline"
                                        onClick={() => { setOverrideText(''); }}
                                        className="border-yellow-500/30 text-yellow-500 hover:bg-yellow-500/10"
                                    >
                                        Reset
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={endRef} />
                </div>

                {/* Input Dock */}
                <div className="p-4 bg-background border-t border-border">
                    <form onSubmit={onSubmit} className="max-w-3xl mx-auto relative flex items-center">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={isWaitingApproval ? "Waiting for manager approval..." : "Simulate customer objection..."}
                            className="pr-12 bg-secondary/30 h-12 border-muted-foreground/20 focus-visible:ring-blue-500/50"
                            disabled={isTyping || isWaitingApproval}
                        />
                        {isTyping ? (
                            <Button type="button" size="icon" variant="ghost" className="absolute right-1 text-red-400 hover:text-red-300 hover:bg-red-400/10" onClick={stopGeneration}>
                                <div className="w-3 h-3 bg-current rounded-sm" />
                            </Button>
                        ) : (
                            <Button type="submit" size="icon" variant="ghost" className="absolute right-1 text-blue-500 hover:text-blue-400 hover:bg-blue-500/10" disabled={!input.trim() || isWaitingApproval}>
                                <Send size={18} />
                            </Button>
                        )}
                    </form>
                </div>

            </div>

            {/* Right Telemetry / Reasoning Panel */}
            <div className="w-full lg:w-96 flex-shrink-0 bg-background overflow-hidden flex flex-col">
                <div className="p-4 border-b border-border font-semibold text-sm flex items-center justify-between">
                    <span>Engine Telemetry</span>
                    <span className="flex items-center gap-1 text-[10px] text-green-500 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-ping" />
                        LIVE
                    </span>
                </div>
                <div className="flex-1 p-4 overflow-hidden">
                    <ReasoningView />
                </div>
            </div>

        </div>
    );
}
