export type SessionStatus = 'in_progress' | 'completed' | 'abandoned';
export type SpeakerType = 'user' | 'ai_customer' | 'coach';

export interface AbilityScores {
  [dimensionId: string]: number; // 0-100
}

export interface TrainingSession {
  id: string;
  user_id: string;
  course_id: string;
  status: SessionStatus;
  score?: number;
  ability_scores?: AbilityScores;
  started_at: string;
  completed_at?: string;
  created_at: string;
}

export interface CoachTip {
  type: 'hint' | 'correction' | 'praise';
  content: string;
}

export interface Conversation {
  id: string;
  session_id: string;
  speaker_type: SpeakerType;
  content: string;
  coach_tips?: CoachTip[];
  created_at: string;
}
