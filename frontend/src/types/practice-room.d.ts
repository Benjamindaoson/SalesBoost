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

export type WSMessage = NPCMessage | CoachMessage;

export interface PracticeRoomProps {
  sessionId: string;
  initialNPCDetails: {
    avatar: string;
    tags: string[];
  };
}

