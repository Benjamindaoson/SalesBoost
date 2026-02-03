import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Send, Mic, Sparkles, AlertCircle, RefreshCw, Loader2, Wifi, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from '@/store/auth.store';
import { sessionService, Session } from '@/services/session.service';
import { useLocation, useParams } from 'react-router-dom';
import { useToast } from "@/hooks/use-toast";
import { useWebSocket } from '@/hooks/useWebSocket';

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

  // WebSocket connection
  const {
    isConnected,
    isConnecting,
    sendMessage,
    lastMessage
  } = useWebSocket({
    url: 'ws://localhost:8000/ws/chat',
    queryParams: {
      token: localStorage.getItem('access_token') || '',
      session_id: (session as any)?.session_id || session?.id || ''
    },
    onConnect: () => {
      console.log('[Training] WebSocket connected');
      toast({
        title: "已连接",
        description: "WebSocket连接成功"
      });
    },
    onDisconnect: () => {
      console.log('[Training] WebSocket disconnected');
    },
    onError: (error) => {
      console.error('[Training] WebSocket error:', error);
    }
  });

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    const message = lastMessage;

    if (message.type === 'init') {
      // Handle initialization message
      console.log('[Training] Session initialized:', message);
      if (message.history && Array.isArray(message.history)) {
        const historyMessages: Message[] = message.history.map((msg: any, idx: number) => ({
          id: `history-${idx}`,
          role: msg.role,
          content: msg.content,
          timestamp: Date.now() - (message.history.length - idx) * 1000
        }));
        setMessages(historyMessages);
      }
    } else if (message.type === 'turn_result') {
      // Handle NPC response
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: message.npc_response || message.content || '',
        timestamp: Date.now()
      }]);
      setIsTyping(false);
    } else if (message.type === 'round_event') {
      // Handle coach tips and other events
      if (message.coach_tip) {
        setTips(prev => [...prev, {
          id: Date.now().toString(),
          content: message.coach_tip.content || message.coach_tip,
          type: message.coach_tip.type || 'suggestion'
        }]);
      }
    } else if (message.type === 'error') {
      console.error('[Training] Server error:', message);
      toast({
        variant: "destructive",
        title: "错误",
        description: message.error || message.message || '服务器错误'
      });
      setIsTyping(false);
    }
  }, [lastMessage, toast]);

  // Initialize session on mount
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
      toast({
        title: "会话已创建",
        description: "训练会话初始化成功"
      });
    } catch (error) {
      console.error("Failed to create session:", error);
      toast({
        variant: "destructive",
        title: "会话创建失败",
        description: "无法启动训练会话，请重试",
        action: <Button variant="outline" size="sm" onClick={initSession}>重试</Button>
      });
    } finally {
      setIsCreatingSession(false);
    }
  };

  useEffect(() => {
    initSession();
  }, [user, courseId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!inputText.trim() || !session || isTyping || !isConnected) return;

    const userMessageContent = inputText;
    setInputText('');

    // Add user message to UI
    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessageContent,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, newUserMessage]);
    setIsTyping(true);

    // Send via WebSocket instead of direct LLM call
    sendMessage({
      type: 'message',
      content: userMessageContent,
      session_id: (session as any)?.session_id || (session as any)?.id
    });
  };


  if (!session && !isCreatingSession) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Failed to load session</h2>
          <Button onClick={initSession}>
            <RefreshCw className="mr-2 h-4 w-4" /> Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Header: Customer Persona */}
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Avatar className="h-12 w-12 border-2 border-indigo-100">
              <AvatarImage src="/customer-avatar.png" />
              <AvatarFallback>AI</AvatarFallback>
            </Avatar>
            <div>
              <h2 className="font-semibold text-gray-900">AI Customer</h2>
              <p className="text-xs text-gray-500">Sales Training Simulation</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <>
                <Wifi className="h-4 w-4 text-green-500" />
                <span className="text-xs text-green-600 font-medium">已连接</span>
              </>
            ) : isConnecting ? (
              <>
                <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
                <span className="text-xs text-yellow-600 font-medium">连接中...</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-red-500" />
                <span className="text-xs text-red-600 font-medium">未连接</span>
              </>
            )}
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6" ref={scrollRef}>
          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
              <div className={cn(
                "max-w-[80%] rounded-2xl px-5 py-3 shadow-sm",
                msg.role === 'user' 
                  ? "bg-indigo-600 text-white rounded-tr-none" 
                  : "bg-white border border-gray-100 text-gray-800 rounded-tl-none"
              )}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex w-full justify-start">
               <div className="bg-white border border-gray-100 text-gray-800 rounded-tl-none max-w-[80%] rounded-2xl px-5 py-3 shadow-sm flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                  <span className="text-sm text-gray-500">Mr. Smith is thinking...</span>
               </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-gray-100">
          <div className="relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type your response..."
              disabled={isTyping}
              className="w-full pl-4 pr-24 py-3 bg-gray-50 border border-gray-200 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
            />
            <div className="absolute right-2 flex items-center space-x-1">
              <Button size="icon" variant="ghost" className="rounded-full hover:bg-gray-200 text-gray-500">
                <Mic className="h-5 w-5" />
              </Button>
              <Button 
                size="icon" 
                onClick={handleSend} 
                disabled={!inputText.trim() || isTyping}
                className="rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-md disabled:bg-gray-300"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar: Coach Tips & Stats */}
      <div className="w-80 flex flex-col gap-4">
        <Card className="flex-1 border-indigo-100 bg-indigo-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-indigo-900 flex items-center justify-between">
              <div className="flex items-center">
                <Sparkles className="w-4 h-4 mr-2 text-indigo-600" />
                AI Coach Insights
              </div>
              {isCoaching && <Loader2 className="h-3 w-3 animate-spin text-indigo-400" />}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 overflow-y-auto max-h-[calc(100vh-20rem)]">
            {tips.length === 0 ? (
              <p className="text-sm text-gray-500 italic text-center py-8">
                Start chatting to receive real-time coaching tips...
              </p>
            ) : (
              tips.slice().reverse().map((tip) => (
                <div key={tip.id} className="bg-white p-3 rounded-lg shadow-sm border border-indigo-100 text-sm animate-in fade-in slide-in-from-right-5 duration-300">
                  <div className="flex items-start gap-2">
                    <AlertCircle className={cn(
                      "w-4 h-4 mt-0.5 shrink-0",
                      tip.type === 'warning' ? "text-red-500" :
                      tip.type === 'praise' ? "text-green-500" : "text-amber-500"
                    )} />
                    <div>
                      <p className="text-gray-700">{tip.content}</p>
                      <span className="text-[10px] uppercase font-bold text-gray-400 mt-1 block">{tip.type}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Session Goals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Empathy</span>
                <span className="font-medium text-green-600">High</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Clarity</span>
                <span className="font-medium text-amber-600">Medium</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5 mt-2">
                <div className="bg-indigo-600 h-1.5 rounded-full w-[70%]"></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
