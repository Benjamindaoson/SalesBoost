import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PlugZap } from "lucide-react";
import type { ReadyState } from "react-use-websocket";

const statusText: Record<number, string> = {
  0: "连接中",
  1: "已连接",
  2: "断开",
  3: "断开",
};

const statusDotClass: Record<number, string> = {
  0: "bg-yellow-500",
  1: "bg-green-500",
  2: "bg-red-500",
  3: "bg-red-500",
};

export function PracticeRoomHeader(props: {
  npc: { avatar: string; tags: string[] };
  readyState: ReadyState;
}) {
  const tags = props.npc.tags.slice(0, 3);
  const stateKey = Number(props.readyState);

  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center gap-3 min-w-0">
        <Avatar className="h-12 w-12 ring-1 ring-gray-200">
          <AvatarImage src={props.npc.avatar} alt="NPC" />
          <AvatarFallback className="bg-gray-100 text-gray-600">NPC</AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-gray-900">实战对练</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Badge
                key={tag}
                variant="secondary"
                className="bg-purple-50 text-purple-700 border-purple-100"
              >
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm text-gray-600">
        <PlugZap className="h-4 w-4 text-gray-400" />
        <span className={cn("h-2 w-2 rounded-full", statusDotClass[stateKey] ?? "bg-gray-300")} />
        <span>{statusText[stateKey] ?? "断开"}</span>
      </div>
    </div>
  );
}

