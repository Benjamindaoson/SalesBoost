// Type definitions for SalesAgent Platform

export interface Lead {
  session_id: string;
  customer_name: string;
  intent_score: number;
  last_message: string;
  last_message_time: string;
  current_stage: string;
  unread_count: number;
  ai_driving: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  is_ai_generated: boolean;
}

export interface Session {
  id: string;
  customer_id?: string;
  current_stage: string;
  status: string;
}

export interface ReasoningOutput {
  customer_signals: {
    objection_type: string;
    decision_stage: string;
    urgency: number;
    interest_level: number;
  };
  recommended_tactics: {
    primary: string;
    secondary: string[];
    tone: string;
    avoid?: string[];
  };
  hidden_concerns: string[];
}

export interface GuardEvent {
  risk_type: string;
  original: string;
  rewritten: string;
}

export interface DailySummary {
  today_followups: number;
  high_intent_count: number;
  deals_closed: number;
  avg_response_time: number;
}

export interface AISuggestion {
  suggestion: string;
  tactics?: {
    primary: string;
    secondary: string[];
    tone: string;
    avoid: string[];
  };
}

export interface OnboardingStatus {
  user_id: string;
  progress: number;
  steps: {
    wechat_binding: boolean;
    knowledge_upload: boolean;
    preferences_set: boolean;
    sandbox_tested: boolean;
    activated: boolean;
  };
}

export interface UserPreferences {
  tone: 'professional' | 'friendly' | 'concise';
  response_speed: number;
  auto_send: boolean;
}
