import { useState, useRef, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Send, Mic, Sparkles, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from '@/store/auth.store';
import { sessionService, Session } from '@/services/session.service';
import { useLocation, useParams } from 'react-router-dom';
import { useToast } from "@/hooks/use-toast";

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
  const { courseId } = useParams(); // Get courseId from URL
  const { toast } = useToast();
  
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Hello! I am Mr. Smith, the purchasing manager at TechCorp. I heard you have a new CRM solution?', timestamp: Date.now() }
  ]);
  const [inputText, setInputText] = useState('');
  const [tips, setTips] = useState<CoachTip[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  
  // Initialize session on mount or retry
  const initSession = async () => {
    if (!user) return;
    setIsCreatingSession(true);
    
    try {
      // Use courseId from URL, fallback to default if not present
      const targetCourseId = courseId || "course_default";
      
      const newSession = await sessionService.createSession({
        user_id: user.id,
        course_id: targetCourseId,
        scenario_id: "scenario_default", // Ideally fetched based on course
        persona_id: "persona_default"    // Ideally fetched based on course
      });
      setSession(newSession);
      toast({
        title: "Session Started",
        description: "Training session initialized successfully.",
      });
    } catch (error) {
      console.error("Failed to create session:", error);
      toast({
        variant: "destructive",
        title: "Session Creation Failed",
        description: "Could not start training session. Please try again.",
        action: <Button variant="outline" size="sm" onClick={initSession}>Retry</Button>
      });
    } finally {
      setIsCreatingSession(false);
    }
  };

  useEffect(() => {
    initSession();
  }, [user, courseId]);

  const { sendSalesMessage, isConnected } = useWebSocket({
    url: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/train',
    queryParams: session ? {
      user_id: user?.id || "default_user",
      session_id: session.id,
      course_id: session.course_id,
      scenario_id: session.scenario_id,
      persona_id: "persona_default" 
    } : undefined,
    onMessage: (msg) => {
      if (msg.type === 'npc_chunk' && !msg.data?.is_final) {
        setMessages(prev => {
           const lastMsg = prev[prev.length - 1];
           if (lastMsg && lastMsg.role === 'assistant' && lastMsg.id === msg.data?.event_id) {
               return prev.map(m => m.id === msg.data?.event_id ? { ...m, content: m.content + msg.data.content } : m);
           } else {
               return [...prev, {
                   id: msg.data?.event_id || Date.now().toString(),
                   role: 'assistant',
                   content: msg.data?.content || '',
                   timestamp: Date.now()
               }];
           }
        });
      } else if (msg.type === 'coach_tip') {
        setTips(prev => [...prev, {
          id: Date.now().toString(),
          content: msg.data.content,
          type: msg.data.tip_type || 'suggestion'
        }]);
      } else if (msg.type === 'error') {
        toast({
          variant: "destructive",
          title: "Connection Error",
          description: msg.data?.message || "An error occurred during training."
        });
      }
    }
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!inputText.trim() || !session) return;
    
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      timestamp: Date.now()
    }]);

    sendSalesMessage(inputText, session.id);
    setInputText('');
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
              <AvatarFallback>CS</AvatarFallback>
            </Avatar>
            <div>
              <h2 className="font-semibold text-gray-900">Mr. Smith</h2>
              <p className="text-xs text-gray-500">Purchasing Manager • Skeptical • TechCorp</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className={cn("h-2.5 w-2.5 rounded-full", isConnected ? "bg-green-500" : "bg-red-500")}></span>
            <span className="text-xs text-gray-500">{isConnected ? 'Live' : 'Disconnected'}</span>
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
              className="w-full pl-4 pr-24 py-3 bg-gray-50 border border-gray-200 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
            <div className="absolute right-2 flex items-center space-x-1">
              <Button size="icon" variant="ghost" className="rounded-full hover:bg-gray-200 text-gray-500">
                <Mic className="h-5 w-5" />
              </Button>
              <Button size="icon" onClick={handleSend} className="rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-md">
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
            <CardTitle className="text-sm font-medium text-indigo-900 flex items-center">
              <Sparkles className="w-4 h-4 mr-2 text-indigo-600" />
              AI Coach Insights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 overflow-y-auto max-h-[calc(100vh-20rem)]">
            {tips.length === 0 ? (
              <p className="text-sm text-gray-500 italic text-center py-8">
                Start chatting to receive real-time coaching tips...
              </p>
            ) : (
              tips.map((tip) => (
                <div key={tip.id} className="bg-white p-3 rounded-lg shadow-sm border border-indigo-100 text-sm animate-in fade-in slide-in-from-right-5 duration-300">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                    <p className="text-gray-700">{tip.content}</p>
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
