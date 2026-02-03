import api from '@/lib/api';

export interface SessionCreate {
  user_id: string;
  course_id: string;
  scenario_id: string;
  persona_id: string;
}

export interface Session {
  id: string;
  session_id?: string; // Compatibility alias
  user_id: string;
  course_id: string;
  scenario_id: string;
  status: string;
  total_turns: number;
  final_score?: number;
  final_stage?: string;
  started_at: string;
  created_at?: string;
  completed_at?: string;
  ended_at?: string;
  task_type?: string;
}

export interface SessionReview {
  session_id: string;
  summary: {
    total_turns: number;
    final_score: number;
    skill_improvement: Record<string, number>;
    matrix_evaluation?: any;
  };
  effective_adoptions?: any[];
  skill_improvement?: Record<string, number>;
  strategy_timeline: Array<{
    turn: number;
    situation: string;
    user_strategy: string;
    golden_strategy: string;
    is_optimal: boolean;
    reason: string;
  }>;
  highlights: {
    effective_adoptions: Array<{
      turn: number;
      technique: string;
      style: string;
      skill_delta: any;
    }>;
    ineffective_attempts: Array<any>;
  };
}

export const sessionService = {
  createSession: async (data: SessionCreate) => {
    const response = await api.post<Session>('/sessions', data);
    return response.data;
  },

  listSessions: async (params?: { user_id?: string; status?: string; page?: number; page_size?: number }) => {
    const response = await api.get<{ items: Session[]; total: number }>('/sessions', { params });
    return response.data;
  },

  getSession: async (sessionId: string) => {
    const response = await api.get<Session>(`/sessions/${sessionId}`);
    return response.data;
  },

  getSessionReview: async (sessionId: string) => {
    const response = await api.get<SessionReview>(`/sessions/${sessionId}/review`);
    return response.data;
  },

  completeSession: async (sessionId: string) => {
    const response = await api.patch<{ message: string; task_id: string }>(`/sessions/${sessionId}/complete`);
    return response.data;
  }
};
