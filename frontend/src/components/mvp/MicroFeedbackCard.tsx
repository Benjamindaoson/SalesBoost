/**
 * MVP 轻量复盘卡片
 * 会话结束后弹出，最多3条反馈，每条带【复制句子】按钮
 */
import { useState } from "react";
import { Copy, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FeedbackItem {
  title: string;
  what_happened: string;
  better_move: string;
  copyable_phrase: string;
}

interface MicroFeedbackCardProps {
  feedbackItems: FeedbackItem[];
  totalTurns: number;
  onClose?: () => void;
  className?: string;
}

export function MicroFeedbackCard({
  feedbackItems,
  totalTurns,
  onClose,
  className,
}: MicroFeedbackCardProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  if (!feedbackItems || feedbackItems.length === 0) {
    return null;
  }

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div
      className={cn(
        "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4",
        className
      )}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-bold text-gray-900">轻量复盘</h2>
            <p className="text-sm text-gray-500 mt-1">
              本次会话共 {totalTurns} 轮对话
            </p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          )}
        </div>

        {/* Feedback Items */}
        <div className="p-6 space-y-4">
          {feedbackItems.map((item, index) => (
            <div
              key={index}
              className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
            >
              <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-sm text-gray-600 mb-2">
                <span className="font-medium">发生了什么：</span>
                {item.what_happened}
              </p>
              <p className="text-sm text-gray-600 mb-3">
                <span className="font-medium">更好的做法：</span>
                {item.better_move}
              </p>
              <div className="bg-gray-50 rounded p-3 mb-3">
                <p className="text-sm text-gray-700 mb-2">{item.copyable_phrase}</p>
                <button
                  onClick={() => handleCopy(item.copyable_phrase, index)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                    copiedIndex === index
                      ? "bg-green-500 text-white"
                      : "bg-blue-500 text-white hover:bg-blue-600"
                  )}
                >
                  {copiedIndex === index ? (
                    <>
                      <Check className="w-4 h-4" />
                      已复制
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      复制句子
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-6 border-t bg-gray-50">
          <p className="text-xs text-gray-500 text-center">
            以上反馈基于本次会话分析，建议在实际对话中灵活运用
          </p>
        </div>
      </div>
    </div>
  );
}

