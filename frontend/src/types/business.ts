export interface CustomerPersona {
  id: string;
  name: string;
  age: number;
  job: string;
  traits: string[];
  description: string;
  creator: string;
  rehearsalCount: number;
  lastRehearsalTime: string; // e.g., "12:29" or "Dec 15"
  avatarColor?: string; // For the gradient background logic
}

export interface HistoryRecord {
  id: string;
  dateTime: string;
  courseName: string;
  customerName: string;
  customerRole: string; // e.g., "35岁 · 企业法务"
  category: string;
  duration: string;
  score: number;
  scoreLevel: 'excellent' | 'good' | 'average' | 'poor';
}

export interface HistoryStats {
  totalRehearsals: number;
  averageScore: number;
  bestScore: number;
  totalDurationMinutes: number;
}
