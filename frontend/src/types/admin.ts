export interface AdminCourse {
  id: string;
  title: string;
  description: string;
  author: string;
  studentCount: number;
  popularity?: number;
  rating?: number;
  category: string;
  tags?: string[];
  status: 'published' | 'draft';
}

export interface AdminTask {
  id: string;
  name: string;
  students: string[]; // List of student names or avatars
  studentGroup: string;
  status: 'in-progress' | 'pending' | 'completed';
  tags: string[];
  creator: string;
  startDate: string;
  endDate: string;
}

export interface TeamAnalysis {
  id: string;
  rank: number;
  name: string;
  memberCount: number;
  trainingCount: number;
  growthRate: number; // Percentage
  score: number;
  scoreLabel: string; // e.g., "优秀", "良好"
  trend: 'up' | 'down' | 'stable';
}

export interface AnalysisKPI {
  teamsCount: number;
  oldStudentsCount: number;
  averageScore: number;
  weeklyTrainingCount: number;
}

export interface KnowledgeItem {
  id: string;
  name: string;
  itemCount: number;
  creator: string;
  description: string;
  permissionGroup: 'public' | 'performance' | 'private'; // 公开组, 成效组
  lastUpdated: string;
}

export interface KnowledgeStats {
  totalCount: number;
  activeUsers: number;
  userGrowth: number;
  avgUsage: number;
  recallRate: number;
  recallGrowth: number;
}
