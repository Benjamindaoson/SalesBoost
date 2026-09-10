import { create } from 'zustand';
import type { ReasoningOutput, GuardEvent } from '../types';

interface AppState {
    // Global
    theme: 'dark' | 'light';
    toggleTheme: () => void;

    // Active Chat Session
    activeSessionId: string | null;
    setActiveSessionId: (id: string | null) => void;

    // Real-time Chat state
    currentReasoning: ReasoningOutput | null;
    setCurrentReasoning: (r: ReasoningOutput | null) => void;

    fsmStage: string;
    setFsmStage: (s: string) => void;
    fsmHistory: string[];
    setFsmHistory: (h: string[]) => void;

    activeGuardEvents: GuardEvent[];
    addGuardEvent: (e: GuardEvent) => void;
    clearGuardEvents: () => void;

    latestRewardScores: Record<string, number> | null;
    setLatestRewardScores: (scores: Record<string, number>) => void;
}

export const useAppStore = create<AppState>((set) => ({
    theme: 'dark',
    toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),

    activeSessionId: null,
    setActiveSessionId: (id) => set({ activeSessionId: id, currentReasoning: null, activeGuardEvents: [], latestRewardScores: null }),

    currentReasoning: null,
    setCurrentReasoning: (r) => set({ currentReasoning: r }),

    fsmStage: 'ICEBREAK',
    setFsmStage: (s) => set({ fsmStage: s }),
    fsmHistory: [],
    setFsmHistory: (h) => set({ fsmHistory: h }),

    activeGuardEvents: [],
    addGuardEvent: (e) => set((state) => ({ activeGuardEvents: [...state.activeGuardEvents, e] })),
    clearGuardEvents: () => set({ activeGuardEvents: [] }),

    latestRewardScores: null,
    setLatestRewardScores: (scores) => set({ latestRewardScores: scores }),
}));
