import axios from 'axios';
import type { Lead, DailySummary, AISuggestion, OnboardingStatus, UserPreferences } from '../types';

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const api = {
  getKnowledgeChunks: async () => (await client.get('/knowledge/chunks')).data,
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return (await client.post('/knowledge/upload', formData)).data;
  },
  testRetrieval: async (query: string) => (await client.post('/knowledge/test-retrieval', { query })).data,
  getPreferencePairs: async () => (await client.get('/flywheel/preference-pairs')).data,
  exportDpo: async () => (await client.get('/flywheel/export-dpo', { responseType: 'blob' })).data,
  triggerApo: async () => (await client.post('/flywheel/apo/trigger')).data,
  getPrompts: async () => (await client.get('/prompts')).data,
};

// Sessions API
export const sessionsApi = {
  getActiveSessions: () => client.get<Lead[]>('/sessions/active'),
  getSession: (sessionId: string) => client.get(`/sessions/${sessionId}`),
  takeoverSession: (sessionId: string) => client.post(`/sessions/${sessionId}/takeover`),
  resumeAI: (sessionId: string) => client.post(`/sessions/${sessionId}/resume-ai`),
  getSuggestion: (sessionId: string) => client.get<AISuggestion>(`/sessions/${sessionId}/suggestion`),
};

// Analytics API
export const analyticsApi = {
  getDailySummary: () => client.get<DailySummary>('/analytics/daily-summary'),
};

// Chat API
export const chatApi = {
  sendMessage: (sessionId: string, content: string) =>
    client.post(`/chat/${sessionId}`, { content }),
  getHistory: (sessionId: string) => client.get(`/chat/${sessionId}/history`),
};

// Onboarding API
export const onboardingApi = {
  getWeChatQR: (userId: string) =>
    client.get<{ qr_url: string; token: string }>(`/onboarding/wechat-qr?user_id=${userId}`),
  uploadKnowledge: (userId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post(`/onboarding/upload-knowledge?user_id=${userId}`, formData);
  },
  setPreferences: (userId: string, preferences: UserPreferences) =>
    client.post(`/onboarding/set-preferences`, null, {
      params: { user_id: userId, ...preferences }
    }),
  testChat: (message: string) =>
    client.post<{ response: string; intent: string; tactics: any }>('/onboarding/test-chat', { message }),
  activate: (userId: string) =>
    client.post(`/onboarding/activate?user_id=${userId}`),
  getStatus: (userId: string) =>
    client.get<OnboardingStatus>(`/onboarding/status/${userId}`),
};

export default client;
