import { Check, CircleDashed } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';

const STAGES = [
    { id: 'ICEBREAK', label: 'Icebreak' },
    { id: 'DISCOVERY', label: 'Discovery' },
    { id: 'PROPOSAL', label: 'Proposal' },
    { id: 'OBJECTION', label: 'Objection' },
    { id: 'CLOSE', label: 'Close' },
];

export function FSMTracker() {
    const { fsmStage, fsmHistory } = useAppStore();

    // Find current index based on history/current stage
    const currentIndex = Math.max(
        STAGES.findIndex(s => s.id === fsmStage),
        ...fsmHistory.map(h => STAGES.findIndex(s => s.id === h))
    );

    return (
        <div className="flex items-center space-x-2 py-4 px-6 bg-card border-b border-border overflow-x-auto w-full max-w-full">
            {STAGES.map((stage, i) => {
                const isCompleted = i <= currentIndex;
                const isActive = stage.id === fsmStage;

                return (
                    <div key={stage.id} className="flex items-center">

                        <div className={`flex flex-col items-center select-none w-24 shrink-0 transition-opacity duration-300 ${isCompleted ? 'opacity-100' : 'opacity-40'}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 mb-2 transition-colors duration-300 ${isActive
                                    ? 'bg-blue-500/20 border-blue-500 text-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)]'
                                    : isCompleted
                                        ? 'bg-primary/20 border-primary text-primary'
                                        : 'bg-background border-muted text-muted-foreground'
                                }`}>
                                {isCompleted && !isActive ? <Check className="w-4 h-4" /> : <CircleDashed className={`w-4 h-4 ${isActive ? 'animate-spin-slow' : ''}`} />}
                            </div>
                            <span className={`text-xs font-medium uppercase tracking-wider ${isActive ? 'text-blue-500' : 'text-muted-foreground'}`}>
                                {stage.label}
                            </span>
                        </div>

                        {i < STAGES.length - 1 && (
                            <div className={`w-12 h-0.5 -mt-6 transition-colors duration-500 ${isCompleted ? 'bg-primary' : 'bg-muted'}`} />
                        )}

                    </div>
                );
            })}
        </div>
    );
}
