import { Task, TaskStats, CustomerPersona, PracticeRecord, PracticeStats } from '@/types';

export const mockTaskStats: TaskStats = {
  total: 5,
  inProgress: 3,
  completed: 1,
  averageScore: 84,
};

export const mockTasks: Task[] = [
  {
    id: '1',
    courseName: '新客户开卡+场景训练',
    courseTags: ['2/5节', '客户开卡', '渠道训练'],
    taskInfo: '第一章 — AI客服训练计划',
    taskLink: '模拟客户',
    status: 'in_progress',
    dateRange: {
      start: '2024-12-01',
      end: '2024-12-31',
    },
    progress: {
      completed: 3,
      total: 5,
      score: 85,
    },
  },
  {
    id: '2',
    courseName: '异议处理训练',
    courseTags: ['3/5节', '处理异议', '场景训练'],
    taskInfo: '销售场景模拟对话',
    taskLink: '模拟客户',
    status: 'not_started',
    dateRange: {
      start: '2024-12-12',
      end: '2024-12-25',
    },
    progress: {
      completed: 0,
      total: 3,
    },
  },
  {
    id: '3',
    courseName: '权益查询场景',
    courseTags: ['4/5节', '客户咨询'],
    taskInfo: '高需客户分类识别',
    status: 'completed',
    dateRange: {
      start: '2024-11-15',
      end: '2024-11-30',
    },
    progress: {
      completed: 5,
      total: 5,
      score: 92,
    },
  },
  {
    id: '4',
    courseName: '合规话术训练',
    courseTags: ['2/9节'],
    taskInfo: '合规提示及规范流程',
    status: 'in_progress',
    dateRange: {
      start: '2024-12-05',
      end: '2024-12-20',
    },
    progress: {
      completed: 2,
      total: 4,
      score: 78,
    },
  },
];

export const mockPersonas: CustomerPersona[] = [
  {
    id: '1',
    name: '刘先生',
    description: '27岁；互联网行业程序员，商旅需求高',
    tags: ['9级别'],
    lastPracticed: '今天17:29',
    level: '9级别',
  },
  {
    id: '2',
    name: '王女士',
    description: '33岁；金融行业，家庭型，关注子女教育',
    tags: [],
    lastPracticed: '今天15:20',
  },
  {
    id: '3',
    name: '李总',
    description: '42岁；企业高管，追求高质量商品服务和品质',
    tags: [],
    lastPracticed: '昨天23:16',
    level: '王芳', // The image showed "王芳" as a tag-like element, possibly the sales rep assigned or a specific tag.
  },
  {
    id: '4',
    name: '张小姐',
    description: '29岁', // Inferred age
    tags: [],
    lastPracticed: '今天10:00', // Mock time
    note: 'Do not sell or share my personal info',
  },
    {
    id: '5',
    name: '赵经理',
    description: '38岁', 
    tags: [],
    lastPracticed: '今天09:00',
  },
    {
    id: '6',
    name: '周女士',
    description: '45岁',
    tags: [],
    lastPracticed: '昨天14:00',
  },
];

export const mockPracticeStats: PracticeStats = {
  totalSessions: 8,
  averageScore: 82,
  highestScore: 92,
  totalDuration: 120,
};

export const mockPracticeRecords: PracticeRecord[] = [
  {
    id: '1',
    dateTime: '2024-12-21 14:30',
    courseInfo: '新客户开卡+场景训练',
    customerRole: '刘先生',
    category: '新客户开卡',
    duration: '15分32秒',
    score: 85,
  },
  {
    id: '2',
    dateTime: '2024-12-20 10:15',
    courseInfo: '异议处理训练',
    customerRole: '王女士',
    category: '异议处理',
    duration: '18分20秒',
    score: 78,
  },
  {
    id: '3',
    dateTime: '2024-12-19 16:45',
    courseInfo: '权益推荐场景', // Image says 权益推荐场景
    customerRole: '李总',
    category: '权益推荐',
    duration: '12分08秒',
    score: 92,
  },
];
