import { useState, useCallback, useRef } from 'react';
import { useAppStore } from '../stores/appStore';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    isStreaming?: boolean;
}

export function useSSE() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const [isWaitingApproval, setIsWaitingApproval] = useState(false);
    const abortController = useRef<AbortController | null>(null);

    const {
        activeSessionId,
        setCurrentReasoning,
        setFsmStage,
        setFsmHistory,
        addGuardEvent,
        clearGuardEvents,
        setLatestRewardScores
    } = useAppStore();

    const sendMessage = useCallback(async (text: string, isResumption: boolean = false) => {
        if (!text.trim() && !isResumption) return;

        // Only add user message if it's not a resumption (which has no new user input)
        if (!isResumption) {
            const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: text };
            setMessages(prev => [...prev, userMsg]);
        }

        setIsTyping(true);
        clearGuardEvents();

        // Add placeholder assistant message for streaming
        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', isStreaming: true }]);

        abortController.current = new AbortController();

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: activeSessionId || undefined,
                    customer_id: 'cust_demo',
                    message: text
                }),
                signal: abortController.current.signal
            });

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || ''; // Keep the last incomplete chunk in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.replace('data: ', '');
                        try {
                            const payload = JSON.parse(dataStr);
                            handleSseEvent(payload, assistantId);
                        } catch (e) {
                            console.error("Failed to parse SSE event", dataStr);
                        }
                    }
                }
            }
        } catch (err: any) {
            if (err.name !== 'AbortError') {
                console.error("Chat SSE Error:", err);
            }
        } finally {
            setIsTyping(false);
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, isStreaming: false } : m));
        }
    }, [activeSessionId]);

    const approveMessage = useCallback(async (overrideText: string | null = null) => {
        if (!activeSessionId) return;

        try {
            const res = await fetch(`/api/sessions/${activeSessionId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ override_text: overrideText })
            });

            if (res.ok) {
                setIsWaitingApproval(false);
                setIsTyping(true);
                // Re-establish SSE stream to receive the response
                // For simplicity in this demo, we'll re-trigger a 'stream' call with empty message if the backend supports resumption
                await sendMessage("", true); // Special flag for resumption
            }
        } catch (err) {
            console.error("Failed to approve message", err);
        }
    }, [activeSessionId]);

    const handleSseEvent = (payload: any, messageId: string) => {
        switch (payload.event) {
            case 'fsm_state':
                setFsmStage(payload.data.stage);
                setFsmHistory(payload.data.history);
                break;
            case 'reasoning':
                setCurrentReasoning(payload.data);
                break;
            case 'token':
                setMessages(prev => prev.map(m => {
                    if (m.id === messageId) {
                        return { ...m, content: m.content + payload.data.token };
                    }
                    return m;
                }));
                break;
            case 'guard':
                addGuardEvent(payload.data);
                break;
            case 'reward':
                setLatestRewardScores(payload.data);
                break;
            case 'done':
                if (payload.data.session_id && !activeSessionId) {
                    useAppStore.getState().setActiveSessionId(payload.data.session_id);
                }
                break;
            case 'wait_approval':
                setIsWaitingApproval(true);
                setIsTyping(false);
                break;
            case 'error':
                setMessages(prev => prev.map(m => {
                    if (m.id === messageId) {
                        return { ...m, content: m.content + `\n\n[System Error: ${payload.data.message}]` };
                    }
                    return m;
                }));
                break;
        }
    };

    const stopGeneration = () => {
        if (abortController.current) {
            abortController.current.abort();
            setIsTyping(false);
        }
    };

    return { messages, isTyping, isWaitingApproval, sendMessage, approveMessage, stopGeneration };
}
