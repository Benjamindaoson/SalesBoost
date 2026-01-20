import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronUp } from "lucide-react";

function formatRelativeTime(timestamp: number) {
  const deltaMs = timestamp - Date.now();
  const deltaSec = Math.round(deltaMs / 1000);
  const abs = Math.abs(deltaSec);

  const rtf = new Intl.RelativeTimeFormat("zh-CN", { numeric: "auto" });
  if (abs < 60) return rtf.format(deltaSec, "second");
  const deltaMin = Math.round(deltaSec / 60);
  if (Math.abs(deltaMin) < 60) return rtf.format(deltaMin, "minute");
  const deltaHr = Math.round(deltaMin / 60);
  if (Math.abs(deltaHr) < 24) return rtf.format(deltaHr, "hour");
  const deltaDay = Math.round(deltaHr / 24);
  return rtf.format(deltaDay, "day");
}

export function CoachHintCard(props: {
  hint: {
    id: string;
    level: "warning" | "suggestion";
    title: string;
    content: string;
    receivedAt: number;
  };
}) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(false);
    const t = window.setTimeout(() => setCollapsed(true), 3000);
    return () => window.clearTimeout(t);
  }, [props.hint.id]);

  const borderClass =
    props.hint.level === "warning" ? "border-yellow-300" : "border-blue-300";
  const badgeClass =
    props.hint.level === "warning" ? "text-yellow-700 bg-yellow-50" : "text-blue-700 bg-blue-50";

  const relative = useMemo(
    () => formatRelativeTime(props.hint.receivedAt),
    [props.hint.receivedAt]
  );

  return (
    <div
      className={cn("rounded-xl border bg-white shadow-sm p-3", borderClass)}
      data-testid="coach-hint"
      data-collapsed={collapsed ? "true" : "false"}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", badgeClass)}>
              {props.hint.level === "warning" ? "警告" : "建议"}
            </span>
            <div className="text-sm font-semibold text-gray-900 truncate">{props.hint.title}</div>
          </div>
          <div className="mt-1 text-xs text-gray-400">{relative}</div>
        </div>
        <button
          type="button"
          className="h-8 w-8 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "展开提示" : "折叠提示"}
        >
          {collapsed ? <ChevronDown className="mx-auto h-4 w-4" /> : <ChevronUp className="mx-auto h-4 w-4" />}
        </button>
      </div>

      {!collapsed && <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">{props.hint.content}</div>}
    </div>
  );
}

