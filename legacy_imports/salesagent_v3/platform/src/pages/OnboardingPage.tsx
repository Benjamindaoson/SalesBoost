import React, { useState } from 'react';
import {
    Upload,
    MessageSquare,
    PlayCircle,
    CheckCircle,
    ArrowRight,
    Search,
    BrainCircuit,
    Sparkles
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export function OnboardingPage() {
    const [step, setStep] = useState(1);

    const steps = [
        { id: 1, title: 'Connect Channel', icon: MessageSquare, description: 'Bind your WeChat or CRM.' },
        { id: 2, title: 'Knowledge Base', icon: Upload, description: 'Upload your sales playbook.' },
        { id: 3, title: 'Sales Persona', icon: BrainCircuit, description: 'Set your tone and style.' },
        { id: 4, title: 'Sandbox Test', icon: PlayCircle, description: 'Test the AI Agent safely.' },
    ];

    return (
        <div className="max-w-4xl mx-auto py-12 px-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="text-center space-y-4 mb-12">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-500 text-xs font-bold uppercase tracking-wider border border-blue-500/20">
                    <Sparkles className="w-3 h-3" />
                    New Agent Setup
                </div>
                <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    Initialize Your SalesAgent Pilot
                </h1>
                <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
                    Complete these 4 steps to deploy your 24/7 AI Sales Intelligence. (Est. time: 30 minutes)
                </p>
            </div>

            {/* Stepper */}
            <div className="flex justify-between mb-12 relative px-4">
                <div className="absolute top-5 left-8 right-8 h-0.5 bg-secondary z-0" />
                {steps.map((s) => (
                    <div key={s.id} className="relative z-10 flex flex-col items-center gap-2">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${step >= s.id ? 'bg-blue-600 border-blue-600' : 'bg-background border-secondary text-muted-foreground'
                            }`}>
                            {step > s.id ? <CheckCircle className="w-6 h-6 text-white" /> : <s.icon className={`w-5 h-5 ${step === s.id ? 'text-white' : ''}`} />}
                        </div>
                        <span className={`text-xs font-semibold ${step >= s.id ? 'text-blue-500' : 'text-muted-foreground'}`}>
                            {s.title}
                        </span>
                    </div>
                ))}
            </div>

            {/* Content Area */}
            <Card className="border-muted/20 bg-card/30 backdrop-blur-md shadow-2xl overflow-hidden">
                <CardContent className="p-8">
                    {step === 1 && (
                        <div className="space-y-6 text-center py-8">
                            <h2 className="text-2xl font-bold">Connect your primary channel</h2>
                            <p className="text-muted-foreground">SalesAgent works where your customers are. Bind your account to start receiving signals.</p>
                            <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                                <Button variant="outline" className="h-24 flex flex-col gap-2 border-muted-foreground/20 hover:border-blue-500/50 hover:bg-blue-500/5 cursor-pointer">
                                    <MessageSquare className="w-8 h-8 text-green-500" />
                                    <span>WeChat (Hook)</span>
                                </Button>
                                <Button variant="outline" className="h-24 flex flex-col gap-2 border-muted-foreground/20 hover:border-blue-500/50 hover:bg-blue-500/5 cursor-pointer">
                                    <Search className="w-8 h-8 text-blue-500" />
                                    <span>Salesforce CRM</span>
                                </Button>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-6 text-center py-8">
                            <h2 className="text-2xl font-bold">Train your Agent on your Product</h2>
                            <p className="text-muted-foreground">Upload your product manual, FAQ, or sales playbook (PDF/Word). AI will index your "Ground Truth".</p>
                            <div className="border-2 border-dashed border-muted-foreground/20 rounded-2xl p-12 transition-colors hover:border-blue-500/30">
                                <Upload className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                                <p className="text-sm">Click to upload or drag & drop</p>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="space-y-6 text-center py-8">
                            <h2 className="text-2xl font-bold">Configure Sales Persona</h2>
                            <p className="text-muted-foreground">How should your Agent speak? Choose a tone that matches your personal brand.</p>
                            <div className="grid grid-cols-3 gap-4">
                                {['Professional', 'Friendly', 'Concise'].map(tone => (
                                    <Button key={tone} variant="outline" className="h-12 border-muted-foreground/20 hover:border-blue-500">{tone}</Button>
                                ))}
                            </div>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="space-y-6 text-center py-8">
                            <h2 className="text-2xl font-bold">Safe Sandbox Simulation</h2>
                            <p className="text-muted-foreground">Try the Agent out yourself before going live. Simulate a tough customer objection.</p>
                            <div className="bg-[#0D0D12] rounded-xl p-4 text-left border border-border h-48 overflow-y-auto mb-4 font-mono text-xs">
                                <div className="text-blue-500">[System]: Sandbox initialized.</div>
                                <div className="text-green-500">[Customer]: Your price is a bit high. Why should I choose you?</div>
                                <div className="animate-pulse">[AI Pilot typing...]</div>
                            </div>
                        </div>
                    )}

                    <div className="flex justify-between mt-8">
                        <Button
                            variant="ghost"
                            disabled={step === 1}
                            onClick={() => setStep(s => s - 1)}
                        >
                            Back
                        </Button>
                        <Button
                            onClick={() => step < 4 ? setStep(s => s + 1) : window.location.href = '/chat'}
                            className="bg-blue-600 hover:bg-blue-700 text-white min-w-[120px]"
                        >
                            {step === 4 ? 'Launch Pilot' : 'Next Step'} <ArrowRight className="ml-2 w-4 h-4" />
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
