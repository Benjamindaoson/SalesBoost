export type TaskStatus = 'not_started' | 'in_progress' | 'completed';

export interface Task {
  id: string;
  courseName: string;
  courseTags: string[];
  taskInfo: string;
  taskLink?: string;
  status: TaskStatus;
  dateRange: {
    start: string;
    end: string;
  };
  progress: {
    completed: number;
    total: number;
    score?: number;
  };
}

export interface TaskStats {
  total: number;
  inProgress: number;
  completed: number;
  averageScore: number;
}

export interface CustomerPersona {
  id: string;
  name: string;
  description: string;
  tags: string[];
  level?: string;
  lastPracticed: string;
  avatar?: string;
  note?: string; // Added based on image (e.g., "Do not sell...")
}

export interface PracticeRecord {
  id: string;
  dateTime: string;
  courseInfo: string;
  customerRole: string;
  category: string;
  duration: string;
  score: number;
}

export interface PracticeStats {
  totalSessions: number;
  averageScore: number;
  highestScore: number;
  totalDuration: number; // Minutes
}

export interface TaskFilter {
  search?: string;
  status?: string; // Changed to string to support 'all'
}

export interface HistoryFilter {
  timeRange?: 'all' | 'week' | 'month';
  scoreRange?: 'all' | 'excellent' | 'good' | 'needs_improvement';
}
