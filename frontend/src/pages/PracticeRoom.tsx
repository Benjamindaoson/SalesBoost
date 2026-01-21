import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { PracticeRoomHeader } from "@/components/practice-room/PracticeRoomHeader";
import { MessageList, type ChatMessage } from "@/components/practice-room/MessageList";
import { MessageInput } from "@/components/practice-room/MessageInput";
import { CoachSidebar, type CoachHint } from "@/components/practice-room/CoachSidebar";
import type {
  CoachMessage,
  NPCMessage,
  PracticeRoomProps,
  TextMessage,
  WSMessage,
} from "@/types/practice-room";
import { cn } from "@/lib/utils";

function makeId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseWSMessage(raw: unknown): WSMessage | null {
  if (!isObject(raw)) return null;
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
  return null;
}

export function PracticeRoom(props: PracticeRoomProps) {
  const wsUrl = useMemo(
    () => {
      const baseUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/api/v1/ws";
      return `${baseUrl}/${props.sessionId}`;
    },
    [props.sessionId]
  );

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [coachHints, setCoachHints] = useState<CoachHint[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sending, setSending] = useState(false);

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
    }, 100);
    return () => window.clearInterval(t);
  }, []);

  const canSend = readyState === ReadyState.OPEN;

  const handleSend = (text: string) => {
    if (!canSend) return;
    const payload: TextMessage = { type: "text", content: text, timestamp: Date.now() };
    setSending(true);

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

  return (
    <div className="-mx-6 -mb-6 -mt-2 h-[calc(100vh-120px)] min-h-[520px]">
      <div className="h-full flex flex-col gap-4">
        <PracticeRoomHeader npc={props.initialNPCDetails} readyState={readyState} />

        <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4">
          <div className={cn("min-h-0 flex flex-col gap-4", sidebarCollapsed ? "lg:w-[calc(100%-48px-16px)]" : "lg:w-[70%]")}> 
            <MessageList className="flex-1 min-h-0" npcAvatar={props.initialNPCDetails.avatar} messages={chatMessages} />
            <MessageInput disabled={!canSend} sending={sending} onSend={handleSend} />
          </div>

          <div className={cn("min-h-0 flex", sidebarCollapsed ? "lg:w-12" : "lg:w-[30%]")}> 
            <CoachSidebar
              collapsed={sidebarCollapsed}
              onToggleCollapsed={() => setSidebarCollapsed((v) => !v)}
              hints={coachHints}
            />
          </div>
        </div>
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

