import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Send, Bot, User as UserIcon, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { title: string; source: string; score: number }[];
  timestamp: number;
}

export default function AssistantPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好！我是你的智能销售助手小安。我可以回答关于产品知识、销售话术、合规要求等问题。\n\n你可以问我：\n- 高端商务卡的年费是多少？\n- 客户嫌贵怎么处理？\n- 信用卡审批流程是怎样的？",
      timestamp: Date.now(),
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/v1/assistant/ask", {
        method: "POST",
        headers: { 
           "Content-Type": "application/json",
           "Authorization": `Bearer ${localStorage.getItem("auth_token")}`
        },
        body: JSON.stringify({ question: userMsg.content }),
      });

      if (!response.ok) throw new Error("Failed to get response");

      const data = await response.json();
      
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        timestamp: Date.now(),
      };

      setMessages(prev => [...prev, botMsg]);
    } catch (error) {
      console.error(error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "抱歉，我遇到了一些问题，请稍后再试。",
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-4xl mx-auto p-4">
      <div className="flex items-center gap-3 mb-6">
         <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600 flex items-center justify-center text-white">
            <Bot className="h-6 w-6" />
         </div>
         <div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
               智能问答助手
            </h1>
            <p className="text-sm text-slate-500">基于 SalesBoost 知识库为您服务</p>
         </div>
      </div>

      <Card className="flex-1 overflow-hidden flex flex-col border-none shadow-md bg-slate-50/50">
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex gap-3 max-w-[80%]",
                msg.role === "user" ? "ml-auto flex-row-reverse" : ""
              )}
            >
              <div className={cn(
                "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
                msg.role === "user" ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-blue-600"
              )}>
                {msg.role === "user" ? <UserIcon className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
              </div>
              
              <div className="space-y-2">
                <div
                  className={cn(
                    "p-3 rounded-2xl text-sm leading-relaxed",
                    msg.role === "user" 
                      ? "bg-slate-900 text-white rounded-tr-sm" 
                      : "bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm"
                  )}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
                
                {msg.sources && msg.sources.length > 0 && (
                   <div className="text-xs text-slate-400 bg-slate-100/50 p-2 rounded-lg border border-slate-100">
                      <div className="font-medium mb-1 flex items-center gap-1">
                         <BookOpenIcon className="h-3 w-3" /> 参考来源:
                      </div>
                      <ul className="list-disc list-inside space-y-1">
                         {msg.sources.map((src, idx) => (
                            <li key={idx} className="truncate max-w-[300px]" title={src.source}>
                               {src.source} ({(src.score * 100).toFixed(0)}%)
                            </li>
                         ))}
                      </ul>
                   </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-3">
               <div className="h-8 w-8 rounded-full bg-white border border-slate-200 text-blue-600 flex items-center justify-center">
                  <Sparkles className="h-5 w-5 animate-pulse" />
               </div>
               <div className="bg-white border border-slate-200 p-3 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1">
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
               </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </CardContent>

        <div className="p-4 bg-white border-t">
           <form 
             onSubmit={(e) => { e.preventDefault(); handleSend(); }}
             className="flex gap-2"
           >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入您的问题..."
                className="flex-1"
                disabled={isLoading}
              />
              <Button type="submit" disabled={isLoading || !input.trim()}>
                 <Send className="h-4 w-4 mr-2" /> 发送
              </Button>
           </form>
        </div>
      </Card>
    </div>
  );
}

function BookOpenIcon(props: any) {
   return (
      <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
   )
}
