import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Send, Mic, Sparkles, AlertCircle, RefreshCw, Loader2, Wifi, WifiOff, Activity, Target } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from '@/store/auth.store';
import { sessionService, Session } from '@/services/session.service';
import { useLocation, useParams } from 'react-router-dom';
import { useToast } from "@/hooks/use-toast";
import { useWebSocket } from '@/hooks/useWebSocket';
import { env } from '@/config/env';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

interface CoachTip {
  id: string;
  content: string;
  type: 'suggestion' | 'warning' | 'praise';
}

export default function Training() {
  const { user } = useAuthStore();
  const location = useLocation();
  const { courseId } = useParams();
  const { toast } = useToast();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [tips, setTips] = useState<CoachTip[]>([]);
  const [isCoaching, setIsCoaching] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  // Telemetry Mock Data (Backend updates could drive this later)
  const [npcMood, setNpcMood] = useState(65);
  const [intent, setIntent] = useState('Greeting');

  const wsUrl = env.VITE_WS_URL ? `${env.VITE_WS_URL}/train` : `ws://${window.location.host}/ws/train`;

  const {
    isConnected,
    isConnecting,
    sendMessage,
    lastMessage
  } = useWebSocket({
    url: wsUrl,
    queryParams: {
      token: localStorage.getItem('access_token') || '',
      session_id: (session as any)?.session_id || session?.id || ''
    },
    onConnect: () => {
      console.log('[Training] WebSocket connected');
      toast({ title: "已连接", description: "神经引擎同步完成", className: "border-primary/50 text-primary" });
    },
    onDisconnect: () => console.log('[Training] WebSocket disconnected'),
    onError: (error) => console.error('[Training] WebSocket error:', error)
  });

  useEffect(() => {
    if (!lastMessage) return;
    const message = lastMessage;

    if (message.type === 'init') {
      if (message.history && Array.isArray(message.history)) {
        const historyMessages: Message[] = message.history.map((msg: any, idx: number) => ({
          id: `history-${idx}`,
          role: msg.role,
          content: msg.content,
          timestamp: Date.now() - ((message.history?.length || 0) - idx) * 1000
        }));
        setMessages(historyMessages);
      }
    } else if (message.type === 'turn_result') {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: message.npc_response || message.npc_reply || message.content || '',
        timestamp: Date.now()
      }]);
      setIsTyping(false);

      // Update Telemetry
      if (message.npc_mood) setNpcMood(message.npc_mood * 100);
      if (message.intent) setIntent(message.intent);

    } else if (message.type === 'round_event') {
      if (message.coach_tip) {
        setTips(prev => [...prev, {
          id: Date.now().toString(),
          content: message.coach_tip.content || message.coach_tip,
          type: message.coach_tip.type || 'suggestion'
        }]);
      }
    } else if (message.type === 'error') {
      toast({ variant: "destructive", title: "通信异常", description: message.error || message.message });
      setIsTyping(false);
    }
  }, [lastMessage, toast]);

  const initSession = async () => {
    if (!user) return;
    setIsCreatingSession(true);
    try {
      const targetCourseId = courseId || "course_default";
      const newSession = await sessionService.createSession({
        user_id: user.id,
        course_id: targetCourseId,
        scenario_id: "scenario_default",
        persona_id: "persona_default"
      });
      setSession(newSession);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "启动失败",
        description: "无法初始化模拟器核心",
      });
    } finally {
      setIsCreatingSession(false);
    }
  };

  useEffect(() => { initSession(); }, [user, courseId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!inputText.trim() || !session || isTyping || !isConnected) return;
    const userMessageContent = inputText;
    setInputText('');

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: userMessageContent,
      timestamp: Date.now()
    }]);
    setIsTyping(true);

    sendMessage({
      type: 'message',
      content: userMessageContent,
      session_id: (session as any)?.session_id || (session as any)?.id
    });
  };

  if (!session && !isCreatingSession) {
    return (
      <div className="flex flex-col h-[calc(100vh-8rem)] items-center justify-center p-6">
        <div className="glass-panel p-10 rounded-2xl flex flex-col items-center max-w-md w-full text-center space-y-6">
          <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center animate-pulse">
            <AlertCircle className="w-8 h-8 text-destructive" />
          </div>
          <div>
            <h2 className="text-2xl font-display font-semibold mb-2">Sim-Core Offline</h2>
            <p className="text-muted-foreground">Unable to establish connection with the SalesBoost neural engine.</p>
          </div>
          <Button onClick={initSession} size="lg" className="w-full font-semibold">
            <RefreshCw className="mr-2 w-5 h-5" /> Reboot Sequence
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-6 overflow-hidden">

      {/* LEFT: Main Simulation UI */}
      <div className="flex-1 flex flex-col glass-panel rounded-3xl border border-white/40 shadow-2xl overflow-hidden relative">

        {/* Dynamic Telemetry Header */}
        <div className="px-6 py-4 border-b border-border/50 bg-background/50 backdrop-blur-md flex items-center justify-between z-10 relative">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Avatar className="h-14 w-14 border-2 border-primary/20 shadow-lg shadow-primary/10">
                <AvatarImage src="/customer-avatar.png" />
                <AvatarFallback className="bg-gradient-to-br from-primary to-accent text-primary-foreground">AI</AvatarFallback>
              </Avatar>
              <div className={cn(
                "absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-background",
                isConnected ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]" :
                  isConnecting ? "bg-amber-500 animate-pulse" : "bg-destructive"
              )} />
            </div>
            <div>
              <h2 className="text-xl font-display font-bold tracking-tight text-foreground flex items-center gap-2">
                TechCorp Lead
                {isConnected && <Badge variant="outline" className="border-emerald-500/30 text-emerald-600 bg-emerald-500/10 text-[10px] uppercase font-bold tracking-wider">LIVE</Badge>}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                  <Activity className="w-3 h-3" /> Sentience Level
                </span>
                <div className="w-24 h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full shadow-[0_0_10px_rgba(99,102,241,0.5)] transition-all duration-500" style={{ width: `${npcMood}%` }} />
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="px-3 py-1.5 text-xs font-semibold gap-1.5 bg-background shadow-sm border border-border">
              <Target className="w-3.5 h-3.5 text-primary" /> Active Intent:
              <span className="text-primary tracking-wide">{intent.toUpperCase()}</span>
            </Badge>
          </div>
        </div>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-32" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-50 space-y-4">
              <Sparkles className="w-12 h-12 text-primary animate-pulse-glow" />
              <p className="text-lg font-medium tracking-tight">Simulation Initialized.<br />You may initiate the pitch.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex w-full animate-in fade-in slide-in-from-bottom-2 duration-300",
              msg.role === 'user' ? "justify-end" : "justify-start"
            )}>
              <div className={cn(
                "max-w-[75%] px-5 py-3.5 shadow-md",
                msg.role === 'user'
                  ? "bg-primary text-primary-foreground rounded-2xl rounded-tr-sm shadow-primary/20"
                  : "bg-background border border-border/60 text-foreground rounded-2xl rounded-tl-sm"
              )}>
                <p className="text-[15px] leading-relaxed whitespace-pre-wrap font-medium">{msg.content}</p>
                <div className={cn("text-[10px] mt-1.5 font-semibold opacity-60", msg.role === 'user' ? "text-right" : "text-left")}>
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex w-full justify-start animate-in fade-in">
              <div className="bg-background border border-border/60 text-foreground rounded-2xl rounded-tl-sm px-5 py-3.5 shadow-sm flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Synthesizing...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Console */}
        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background via-background/95 to-transparent pt-12">
          <div className="relative flex items-center max-w-4xl mx-auto shadow-2xl shadow-primary/5 rounded-full">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Inject your response..."
              disabled={isTyping || !isConnected}
              className="w-full pl-6 pr-32 py-4 bg-background border-2 border-border/50 rounded-full focus:outline-none focus:border-primary/50 focus:ring-4 focus:ring-primary/10 transition-all disabled:opacity-50 text-base font-medium placeholder:text-muted-foreground/50 shadow-inner"
            />
            <div className="absolute right-3 flex items-center space-x-2">
              <Button size="icon" variant="ghost" className="rounded-full text-muted-foreground hover:bg-secondary/50 hover:text-foreground">
                <Mic className="h-5 w-5" />
              </Button>
              <Button
                size="icon"
                onClick={handleSend}
                disabled={!inputText.trim() || isTyping || !isConnected}
                className="rounded-full w-10 h-10 shadow-lg hover:shadow-primary/40 disabled:bg-muted disabled:text-muted-foreground transition-all duration-300 transform active:scale-95"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT: AI Coach HUD */}
      <div className="w-96 flex flex-col gap-6">

        {/* Active Insights Card */}
        <Card className="flex-1 bg-gradient-to-b from-ai-surface/40 to-background border-ai-core/20 shadow-xl overflow-hidden relative group">
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay pointer-events-none"></div>

          <CardHeader className="pb-4 relative z-10 border-b border-ai-core/10 bg-background/50 backdrop-blur-sm">
            <CardTitle className="text-sm font-display font-bold text-foreground flex items-center justify-between uppercase tracking-widest">
              <div className="flex items-center text-ai-core">
                <Sparkles className="w-4 h-4 mr-2 animate-pulse" />
                Copilot Insights
              </div>
              <div className="flex items-center gap-2">
                {isCoaching && <Badge variant="outline" className="border-ai-core/30 text-ai-core animate-pulse"><Loader2 className="w-3 h-3 mr-1 animate-spin" /> Analyzing</Badge>}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4 overflow-y-auto h-full relative z-10 custom-scrollbar pb-20">
            {tips.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-40 py-12">
                <Target className="w-10 h-10 mb-3 text-ai-core" />
                <p className="text-sm font-medium">Awaiting interaction data to generate tactical insights.</p>
              </div>
            ) : (
              tips.slice().reverse().map((tip, idx) => (
                <div key={tip.id}
                  className={cn(
                    "p-4 rounded-xl shadow-sm border text-sm animate-in fade-in slide-in-from-right-4 duration-500",
                    tip.type === 'warning' ? "bg-destructive/5 border-destructive/20" :
                      tip.type === 'praise' ? "bg-emerald-500/5 border-emerald-500/20" : "bg-ai-core/5 border-ai-core/20"
                  )}
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "p-1.5 rounded-lg shrink-0 mt-0.5",
                      tip.type === 'warning' ? "bg-destructive/10 text-destructive" :
                        tip.type === 'praise' ? "bg-emerald-500/10 text-emerald-600" : "bg-ai-core/10 text-ai-core"
                    )}>
                      <AlertCircle className="w-4 h-4" />
                    </div>
                    <div>
                      <span className={cn(
                        "text-[10px] uppercase font-bold tracking-widest mb-1 block",
                        tip.type === 'warning' ? "text-destructive" :
                          tip.type === 'praise' ? "text-emerald-600" : "text-ai-core"
                      )}>{tip.type}</span>
                      <p className="text-foreground/90 leading-relaxed font-medium">{tip.content}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Real-time Evaluation Card */}
        <Card className="h-48 shrink-0 glass-panel border-border shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest font-bold text-muted-foreground">Session Parameters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-foreground">Empathy Routing</span>
                  <span className="font-bold text-emerald-500">OPTIMAL</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full w-[85%] shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-foreground">Objection Handling</span>
                  <span className="font-bold text-amber-500">DETECTING</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2 overflow-hidden relative">
                  <div className="bg-amber-500 h-full rounded-full w-[45%] shadow-[0_0_10px_rgba(245,158,11,0.5)]"></div>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent w-full h-full animate-shimmer" style={{ backgroundSize: '200% 100%' }}></div>
                </div>
              </div>

            </div>
          </CardContent>
        </Card>

      </div>

    </div>
  );
}

