/**
 * MVP 实时辅助面板 - 一句话话术
 * 展示 intent_label, suggested_reply, 复制发送/换一句按钮
 */
import { useState } from "react";
import { Copy, RefreshCw, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickSuggestPanelProps {
  intentLabel?: string;
  suggestedReply?: string;
  altReplies?: string[];
  confidence?: number;
  onCopySend?: (text: string) => void;
  className?: string;
}

export function QuickSuggestPanel({
  intentLabel,
  suggestedReply,
  altReplies = [],
  confidence,
  onCopySend,
  className,
}: QuickSuggestPanelProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  if (!suggestedReply) {
    return null;
  }

  // 获取当前显示的建议
  const currentReply = currentIndex === 0 
    ? suggestedReply 
    : altReplies[currentIndex - 1] || suggestedReply;

  const handleCopySend = () => {
    if (onCopySend) {
      onCopySend(currentReply);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      // Fallback: 复制到剪贴板
      navigator.clipboard.writeText(currentReply);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSwitch = () => {
    const totalOptions = 1 + altReplies.length;
    setCurrentIndex((prev) => (prev + 1) % totalOptions);
  };

  // 意图标签颜色映射
  const intentColors: Record<string, string> = {
    权益问答: "bg-blue-100 text-blue-800",
    异议处理: "bg-orange-100 text-orange-800",
    推进成交: "bg-green-100 text-green-800",
    合规风险: "bg-red-100 text-red-800",
    其他: "bg-gray-100 text-gray-800",
  };

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 p-4 shadow-sm", className)}>
      {/* 意图标签 */}
      {intentLabel && (
        <div className="flex items-center gap-2 mb-3">
          <span
            className={cn(
              "px-2 py-1 rounded text-xs font-medium",
              intentColors[intentLabel] || intentColors["其他"]
            )}
          >
            {intentLabel}
          </span>
          {confidence !== undefined && (
            <span className="text-xs text-gray-500">
              置信度: {Math.round(confidence * 100)}%
            </span>
          )}
        </div>
      )}

      {/* 建议话术 */}
      <div className="mb-3">
        <p className="text-sm text-gray-700 leading-relaxed">{currentReply}</p>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button
          onClick={handleCopySend}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
            copied
              ? "bg-green-500 text-white"
              : "bg-blue-500 text-white hover:bg-blue-600"
          )}
        >
          {copied ? (
            <>
              <Check className="w-4 h-4" />
              已复制
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              复制发送
            </>
          )}
        </button>

        {altReplies.length > 0 && (
          <button
            onClick={handleSwitch}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
            title={`${currentIndex + 1}/${1 + altReplies.length}`}
          >
            <RefreshCw className="w-4 h-4" />
            换一句
          </button>
        )}
      </div>
    </div>
  );
}

