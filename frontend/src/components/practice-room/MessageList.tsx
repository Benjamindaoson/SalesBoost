import { useMemo, useState } from "react";
import { Virtuoso } from "react-virtuoso";
import { cn } from "@/lib/utils";
import { NPCMessageItem } from "./NPCMessageItem";
import { UserMessageItem } from "./UserMessageItem";

export type ChatMessage =
  | {
      id: string;
      role: "npc";
      content: string;
      emotion?: string;
      receivedAt: number;
    }
  | {
      id: string;
      role: "user";
      content: string;
      timestamp: number;
    };

export function MessageList(props: {
  className?: string;
  npcAvatar: string;
  messages: ChatMessage[];
}) {
  const [autoFollow, setAutoFollow] = useState(true);
  const messages = props.messages;
  const totalCount = messages.length;

  const followOutput = useMemo(() => {
    if (!autoFollow) return false;
    return "smooth" as const;
  }, [autoFollow]);

  return (
    <div className={cn("h-full rounded-xl border bg-white shadow-sm overflow-hidden", props.className)}>
      <Virtuoso
        data={messages}
        atBottomStateChange={(atBottom) => setAutoFollow(atBottom)}
        followOutput={followOutput}
        itemContent={(_, item) => {
          if (item.role === "npc") {
            return (
              <NPCMessageItem
                key={item.id}
                avatar={props.npcAvatar}
                content={item.content}
              />
            );
          }
          return <UserMessageItem key={item.id} content={item.content} />;
        }}
        components={{
          Footer: () => (totalCount === 0 ? <div className="p-6 text-sm text-gray-400">开始对练吧，向客户问一个问题。</div> : null),
        }}
        className="h-full"
      />
    </div>
  );
}
