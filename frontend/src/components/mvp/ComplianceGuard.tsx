/**
 * MVP 合规防护组件
 * 输入框 debounce 检测，WARN/BLOCK 时显示轻提示 + 一键替换
 */
import { useState, useEffect, useRef } from "react";
import { AlertTriangle, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface ComplianceGuardProps {
  text: string;
  onCheck: (text: string) => Promise<{
    risk_level: "OK" | "WARN" | "BLOCK";
    risk_tags?: string[];
    safe_rewrite?: string;
    reason?: string;
  }>;
  onReplace?: (text: string) => void;
  className?: string;
}

export function ComplianceGuard({
  text,
  onCheck,
  onReplace,
  className,
}: ComplianceGuardProps) {
  const [checkResult, setCheckResult] = useState<{
    risk_level: "OK" | "WARN" | "BLOCK";
    risk_tags?: string[];
    safe_rewrite?: string;
    reason?: string;
  } | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Debounce 500ms
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!text.trim()) {
      setCheckResult(null);
      return;
    }

    setIsChecking(true);
    debounceTimerRef.current = setTimeout(async () => {
      try {
        const result = await onCheck(text);
        setCheckResult(result);
      } catch (error) {
        console.error("Compliance check failed:", error);
      } finally {
        setIsChecking(false);
      }
    }, 500);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [text, onCheck]);

  if (!checkResult || checkResult.risk_level === "OK") {
    return null;
  }

  const isBlocked = checkResult.risk_level === "BLOCK";
  const isWarning = checkResult.risk_level === "WARN";

  return (
    <div
      className={cn(
        "rounded-lg border p-3 text-sm",
        isBlocked
          ? "bg-red-50 border-red-200"
          : "bg-orange-50 border-orange-200",
        className
      )}
    >
      <div className="flex items-start gap-2">
        {isBlocked ? (
          <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
        )}

        <div className="flex-1">
          <p className="font-medium mb-1">
            {isBlocked ? "发送被禁用" : "合规提示"}
          </p>
          <p className="text-gray-700 mb-2">
            {checkResult.reason || "这句话有合规风险"}
          </p>

          {checkResult.safe_rewrite && (
            <div className="bg-white rounded p-2 mb-2 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">建议这样说：</p>
              <p className="text-sm text-gray-800">{checkResult.safe_rewrite}</p>
            </div>
          )}

          {checkResult.risk_tags && checkResult.risk_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {checkResult.risk_tags.map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {checkResult.safe_rewrite && onReplace && (
            <button
              onClick={() => onReplace(checkResult.safe_rewrite!)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              一键替换
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

