import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { CoachHintCard } from "./CoachHintCard";

export type CoachHint = {
  id: string;
  level: "warning" | "suggestion";
  title: string;
  content: string;
  receivedAt: number;
};

export function CoachSidebar(props: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  hints: CoachHint[];
}) {
  return (
    <aside
      className={cn(
        "h-full rounded-xl border bg-white shadow-sm overflow-hidden flex flex-col",
        props.collapsed ? "w-12" : "w-full"
      )}
      aria-label="AI 实时指导"
    >
      <div className={cn("flex items-center justify-between gap-2 border-b px-3 py-3", props.collapsed && "px-2")}> 
        {!props.collapsed && <div className="text-sm font-semibold text-gray-900">AI 实时指导</div>}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-lg text-gray-500 hover:bg-gray-50"
          onClick={props.onToggleCollapsed}
          aria-label={props.collapsed ? "展开侧边栏" : "折叠侧边栏"}
        >
          {props.collapsed ? <PanelRightOpen className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
        </Button>
      </div>

      {props.collapsed ? (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <div className="h-2 w-2 rounded-full bg-[#4F9BFF]" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {props.hints.length === 0 ? (
            <div className="rounded-lg border border-dashed p-4 text-sm text-gray-400">
              暂无指导消息。
            </div>
          ) : (
            props.hints.map((hint) => <CoachHintCard key={hint.id} hint={hint} />)
          )}
        </div>
      )}
    </aside>
  );
}

