export interface TextMessage {
  type: "text";
  content: string;
  timestamp: number;
}

export interface NPCMessage {
  role: "npc";
  content: string;
  emotion?: string;
}

export interface CoachMessage {
  role: "coach";
  type: "coach_hint";
  level: "warning" | "suggestion";
  title: string;
  content: string;
}

export interface EndSessionMessage {
  role: "system";
  type: "session_end";
  reportId?: string;
  reason?: string;
}

export type WSMessage = Partial<NPCMessage> &
  Partial<CoachMessage> &
  Partial<EndSessionMessage> & {
    type?: string;
    npc_response?: string;
    npc_mood?: string;
    coach_suggestion?: string;
    quick_suggest?: {
      intent_label?: string;
      suggested_reply?: string;
      alt_replies?: string[];
      confidence?: number;
    };
    adoption_analysis?: {
      is_effective?: boolean;
      feedback_text?: string;
    };
    micro_feedback?: {
      feedback_items?: any[];
      total_turns?: number;
    };
  };

export interface PracticeRoomProps {
  sessionId: string;
  initialNPCDetails: {
    avatar: string;
    tags: string[];
  };
}
