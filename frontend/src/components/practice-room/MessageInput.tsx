import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Mic, Send } from "lucide-react";

function canUseMediaRecorder() {
  return typeof window !== "undefined" && "MediaRecorder" in window && !!navigator.mediaDevices?.getUserMedia;
}

export function MessageInput(props: {
  disabled?: boolean;
  sending?: boolean;
  onSend: (text: string) => void;
}) {
  const [value, setValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const trimmed = value.trim();
  const canSend = !props.disabled && !props.sending && trimmed.length > 0;

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = async () => {
    if (!canUseMediaRecorder()) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        chunksRef.current = [];
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state === "recording") {
      recorder.stop();
    }
    setIsRecording(false);
  };

  const send = () => {
    if (!canSend) return;
    props.onSend(trimmed);
    setValue("");
  };

  return (
    <div className="rounded-xl border bg-white shadow-sm p-3">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="输入你的话术，Shift+Enter 换行…"
          className={cn(
            "min-h-[44px] max-h-32 flex-1 resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none",
            "focus:border-purple-300 focus:ring-2 focus:ring-purple-100"
          )}
          rows={1}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          disabled={props.disabled}
        />

        <Button
          type="button"
          variant="outline"
          size="icon"
          className={cn(
            "h-11 w-11 rounded-full border-gray-200",
            isRecording ? "border-red-300 bg-red-50 text-red-600" : "text-gray-600"
          )}
          onPointerDown={(e) => {
            e.preventDefault();
            startRecording();
          }}
          onPointerUp={(e) => {
            e.preventDefault();
            stopRecording();
          }}
          onPointerLeave={() => stopRecording()}
          aria-label="按住录音"
          disabled={props.disabled}
        >
          <Mic className="h-4 w-4" />
        </Button>

        <Button
          type="button"
          className={cn(
            "h-11 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 px-5 text-white shadow-sm",
            !canSend ? "opacity-50" : "hover:from-purple-600 hover:to-blue-600"
          )}
          onClick={send}
          disabled={!canSend}
          aria-label="发送"
        >
          <Send className="mr-2 h-4 w-4" />
          {props.sending ? "发送中" : "发送"}
        </Button>
      </div>
      <div className="mt-2 text-xs text-gray-400">
        {props.disabled ? "连接断开，正在尝试重连…" : isRecording ? "录音中（松开结束）" : ""}
      </div>
    </div>
  );
}

