import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { PracticeRoomHeader } from "@/components/practice-room/PracticeRoomHeader";
import { MessageList, type ChatMessage } from "@/components/practice-room/MessageList";
import { MessageInput } from "@/components/practice-room/MessageInput";
import { CoachSidebar, type CoachHint } from "@/components/practice-room/CoachSidebar";
import { QuickSuggestPanel } from "@/components/mvp/QuickSuggestPanel";
import { ComplianceGuard } from "@/components/mvp/ComplianceGuard";
import { MicroFeedbackCard } from "@/components/mvp/MicroFeedbackCard";
import type {
  CoachMessage,
  NPCMessage,
  EndSessionMessage,
  PracticeRoomProps,
  TextMessage,
  WSMessage,
} from "@/types/practice-room";
import { cn } from "@/lib/utils";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

function makeId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseWSMessage(raw: unknown): WSMessage | any {
  if (!isObject(raw)) return null;
  
  // 处理后端返回的 turn_result 消息
  if (raw.type === "turn_result" || raw.type === "turn_result_partial" || raw.type === "session_complete" || raw.type === "init") {
    return raw; // 直接返回，由 useEffect 处理
  }
  
  // 处理旧格式消息（兼容性）
  if (raw.role === "npc" && typeof raw.content === "string") {
    const msg: NPCMessage = {
      role: "npc",
      content: raw.content,
      emotion: typeof raw.emotion === "string" ? raw.emotion : undefined,
    };
    return msg;
  }
  if (
    raw.role === "coach" &&
    raw.type === "coach_hint" &&
    (raw.level === "warning" || raw.level === "suggestion") &&
    typeof raw.title === "string" &&
    typeof raw.content === "string"
  ) {
    const msg: CoachMessage = {
      role: "coach",
      type: "coach_hint",
      level: raw.level,
      title: raw.title,
      content: raw.content,
    };
    return msg;
  }
  if (
    raw.role === "system" &&
    raw.type === "session_end"
  ) {
    const msg: EndSessionMessage = {
      role: "system",
      type: "session_end",
      reportId: typeof raw.reportId === "string" ? raw.reportId : undefined,
      reason: typeof raw.reason === "string" ? raw.reason : undefined,
    };
    return msg;
  }
  return null;
}

export function PracticeRoom(props: PracticeRoomProps) {
  const navigate = useNavigate();
  const wsUrl = useMemo(
    () => {
      const baseUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
      // 使用 session_id 参数连接 WebSocket
      return `${baseUrl}/ws/train?session_id=${props.sessionId}`;
    },
    [props.sessionId]
  );

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [coachHints, setCoachHints] = useState<CoachHint[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sending, setSending] = useState(false);
  
  // MVP 状态
  const [quickSuggest, setQuickSuggest] = useState<{
    intentLabel?: string;
    suggestedReply?: string;
    altReplies?: string[];
    confidence?: number;
  } | null>(null);
  const [inputText, setInputText] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackData, setFeedbackData] = useState<{
    feedbackItems: any[];
    totalTurns: number;
  } | null>(null);

  const incomingQueueRef = useRef<WSMessage[]>([]);

  const { sendJsonMessage, readyState } = useWebSocket(wsUrl, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
    retryOnError: true,
    onMessage: (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const msg = parseWSMessage(parsed);
        if (msg) incomingQueueRef.current.push(msg);
      } catch {
        return;
      }
    },
  });

  useEffect(() => {
    const t = window.setInterval(() => {
      const next = incomingQueueRef.current.shift();
      if (!next) return;

      // 处理后端返回的消息格式
      if (next.type === "session_complete") {
        // MVP: 显示轻量复盘
        if (next.micro_feedback) {
          setFeedbackData({
            feedbackItems: next.micro_feedback.feedback_items || [],
            totalTurns: next.micro_feedback.total_turns || 0,
          });
          setShowFeedback(true);
        } else {
          navigate("/history");
        }
        return;
      }
      
      if (next.role === "system" && next.type === "session_end") {
        navigate("/history");
        return;
      }

      const handleTurnResult = (appendNpc: boolean) => {
        // NPC 消息
        if (next.npc_response) {
          setChatMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (appendNpc && lastMessage?.role === "npc") {
              const updated = [
                ...prev.slice(0, -1),
                {
                  ...lastMessage,
                  content: `${lastMessage.content}${next.npc_response}`,
                  emotion: next.npc_mood ? String(next.npc_mood) : lastMessage.emotion,
                },
              ];
              return updated.length > 2000 ? updated.slice(updated.length - 2000) : updated;
            }

            const item: ChatMessage = {
              id: makeId(),
              role: "npc",
              content: next.npc_response,
              emotion: next.npc_mood ? String(next.npc_mood) : undefined,
              receivedAt: Date.now(),
            };
            const updated = [...prev, item];
            return updated.length > 2000 ? updated.slice(updated.length - 2000) : updated;
          });
        }

        // Coach 建议
        if (next.coach_suggestion) {
          const hint: CoachHint = {
            id: makeId(),
            level: "suggestion",
            title: "教练建议",
            content: next.coach_suggestion,
            receivedAt: Date.now(),
          };
          setCoachHints((prev) => {
            const updated = [hint, ...prev];
            return updated.length > 200 ? updated.slice(0, 200) : updated;
          });
        }

        // MVP: 处理快速建议
        if (next.quick_suggest) {
          setQuickSuggest({
            intentLabel: next.quick_suggest.intent_label,
            suggestedReply: next.quick_suggest.suggested_reply,
            altReplies: next.quick_suggest.alt_replies || [],
            confidence: next.quick_suggest.confidence,
          });
        }
        
        // 如果有采纳分析反馈
        if (next.adoption_analysis?.feedback_text) {
          const feedbackHint: CoachHint = {
            id: makeId(),
            level: next.adoption_analysis.is_effective ? "suggestion" : "warning",
            title: "能力反馈",
            content: next.adoption_analysis.feedback_text,
            receivedAt: Date.now(),
          };
          setCoachHints((prev) => {
            const updated = [feedbackHint, ...prev];
            return updated.length > 200 ? updated.slice(0, 200) : updated;
          });
        }
      };

      // 处理 turn_result 消息（后端主要消息格式）
      if (next.type === "turn_result") {
        handleTurnResult(false);
        return;
      }

      if (next.type === "turn_result_partial") {
        handleTurnResult(true);
        return;
      }

      // 处理旧格式消息（兼容性）
      if (next.role === "system" && next.type === "session_end") {
        if (next.reportId) {
          navigate(`/history`);
        } else {
          navigate("/dashboard");
        }
        return;
      }

      if (next.role === "npc") {
        const item: ChatMessage = {
          id: makeId(),
          role: "npc",
          content: next.content,
          emotion: next.emotion,
          receivedAt: Date.now(),
        };
        setChatMessages((prev) => {
          const updated = [...prev, item];
          return updated.length > 2000 ? updated.slice(updated.length - 2000) : updated;
        });
        return;
      }

      if (next.role === "coach") {
        const hint: CoachHint = {
          id: makeId(),
          level: next.level,
          title: next.title,
          content: next.content,
          receivedAt: Date.now(),
        };
        setCoachHints((prev) => {
          const updated = [hint, ...prev];
          return updated.length > 200 ? updated.slice(0, 200) : updated;
        });
      }
    }, 100);
    return () => window.clearInterval(t);
  }, [navigate]);

  const canSend = readyState === ReadyState.OPEN;

  // MVP: 合规检测函数
  const handleComplianceCheck = async (text: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/mvp/compliance/check?session_id=${props.sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, context: {} }),
      });
      if (!response.ok) throw new Error("Compliance check failed");
      return await response.json();
    } catch (error) {
      console.error("Compliance check error:", error);
      return { risk_level: "OK" };
    }
  };

  const handleSend = (text: string) => {
    if (!canSend) return;
    const payload: TextMessage = { type: "text", content: text, timestamp: Date.now() };
    setSending(true);
    
    // 清空快速建议
    setQuickSuggest(null);

    setChatMessages((prev) => {
      const updated: ChatMessage[] = [
        ...prev,
        { id: makeId(), role: "user", content: text, timestamp: payload.timestamp },
      ];
      return updated.length > 2000 ? updated.slice(updated.length - 2000) : updated;
    });

    sendJsonMessage(payload);
    window.setTimeout(() => setSending(false), 200);
  };
  
  const handleCopySend = (text: string) => {
    setInputText(text);
    // 延迟发送，让用户看到文本
    setTimeout(() => {
      handleSend(text);
    }, 100);
  };
  
  const handleReplaceText = (text: string) => {
    setInputText(text);
  };

  return (
    <div className="-mx-6 -mb-6 -mt-2 h-[calc(100vh-120px)] min-h-[520px]">
      <div className="h-full flex flex-col gap-4">
        <PracticeRoomHeader npc={props.initialNPCDetails} readyState={readyState} />

        <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4">
          <div className={cn("min-h-0 flex flex-col gap-4", sidebarCollapsed ? "lg:w-[calc(100%-48px-16px)]" : "lg:w-[70%]")}> 
            <MessageList className="flex-1 min-h-0" npcAvatar={props.initialNPCDetails.avatar} messages={chatMessages} />
            
            {/* MVP: 快速建议面板 */}
            {quickSuggest && (
              <QuickSuggestPanel
                intentLabel={quickSuggest.intentLabel}
                suggestedReply={quickSuggest.suggestedReply}
                altReplies={quickSuggest.altReplies}
                confidence={quickSuggest.confidence}
                onCopySend={handleCopySend}
              />
            )}
            
            {/* MVP: 合规防护 */}
            {inputText && (
              <ComplianceGuard
                text={inputText}
                onCheck={handleComplianceCheck}
                onReplace={handleReplaceText}
              />
            )}
            
            <MessageInput 
              disabled={!canSend} 
              sending={sending} 
              onSend={handleSend}
              value={inputText}
              onChange={setInputText}
            />
          </div>

          <div className={cn("min-h-0 flex", sidebarCollapsed ? "lg:w-12" : "lg:w-[30%]")}> 
            <CoachSidebar
              collapsed={sidebarCollapsed}
              onToggleCollapsed={() => setSidebarCollapsed((v) => !v)}
              hints={coachHints}
            />
          </div>
        </div>
        
        {/* MVP: 轻量复盘卡片 */}
        {showFeedback && feedbackData && (
          <MicroFeedbackCard
            feedbackItems={feedbackData.feedbackItems}
            totalTurns={feedbackData.totalTurns}
            onClose={() => {
              setShowFeedback(false);
              navigate("/history");
            }}
          />
        )}
      </div>
    </div>
  );
}

export default function PracticeRoomPage() {
  const params = useParams();
  const location = useLocation();
  const sessionId = params.sessionId ?? "";

  const initialNPCDetails =
    (location.state as { initialNPCDetails?: { avatar: string; tags: string[] } } | null)?.
      initialNPCDetails ??
    {
      avatar: "/favicon.svg",
      tags: ["高需求客户", "异议处理", "场景对练"],
    };

  return (
    <PracticeRoom
      sessionId={sessionId}
      initialNPCDetails={{
        avatar: initialNPCDetails.avatar,
        tags: initialNPCDetails.tags.slice(0, 3),
      }}
    />
  );
}
