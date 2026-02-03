export interface Task {
  id: string;
  courseName: string;
  courseSubtitle?: string;
  taskInfo: string;
  taskTag: string;
  status: 'pending' | 'in-progress' | 'completed' | 'paused';
  timeRange: {
    start: string;
    end: string;
  };
  progress: {
    completed: number;
    total: number;
    bestScore?: number;
  };
  participants?: number;
  instructor?: string;
}

export interface Statistics {
  totalTasks: number;
  inProgress: number;
  completed: number;
  averageScore: number;
  lockedItems?: number;
}
