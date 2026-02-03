import { Task, Statistics } from '@/types/dashboard';
import { CustomerPersona, HistoryRecord, HistoryStats } from '@/types/business';

export const mockStatistics: Statistics = {
  totalTasks: 5,
  inProgress: 3,
  completed: 1,
  averageScore: 84,
  lockedItems: 0
};

export const mockCustomers: CustomerPersona[] = [
  {
    id: '1',
    name: '外先生',
    age: 27,
    job: '互联网产品经理',
    traits: ['常跑健身房'],
    description: '27岁 · 互联网产品经理 · 常跑健身房',
    creator: '微聊',
    rehearsalCount: 9,
    lastRehearsalTime: '12:29',
    avatarColor: 'from-blue-400 to-indigo-500'
  },
  {
    id: '2',
    name: '三女士',
    age: 35,
    job: '企业法务',
    traits: ['偏冷静务实风格'],
    description: '35岁 · 企业法务 · 偏冷静务实风格',
    creator: '王静',
    rehearsalCount: 9,
    lastRehearsalTime: '21:16',
    avatarColor: 'from-purple-400 to-pink-500'
  },
  {
    id: '3',
    name: '李Q',
    age: 47,
    job: '企业法务',
    traits: ['注重流程与合规'],
    description: '47岁 · 企业法务 · 注重流程与合规',
    creator: '王静',
    rehearsalCount: 9,
    lastRehearsalTime: '15:16',
    avatarColor: 'from-green-400 to-teal-500'
  },
  {
    id: '4',
    name: '骆小昭',
    age: 29,
    job: '设计师',
    traits: ['生活方式品味控'],
    description: '29岁 · 设计师 · 生活方式品味控',
    creator: '王静',
    rehearsalCount: 8,
    lastRehearsalTime: '10:01',
    avatarColor: 'from-orange-400 to-red-500'
  },
  {
    id: '5',
    name: '虫宜琪',
    age: 45,
    job: '销售总监',
    traits: ['快速决策偏好'],
    description: '45岁 · 销售总监 · 快速决策偏好',
    creator: '王静',
    rehearsalCount: 0,
    lastRehearsalTime: '12月15日 10:31',
    avatarColor: 'from-indigo-400 to-purple-600'
  },
  {
    id: '6',
    name: '用女士',
    age: 45,
    job: '财务',
    traits: ['注重数字与数据统计'],
    description: '45岁 · 财务 · 注重数字与数据统计',
    creator: '为雅',
    rehearsalCount: 0,
    lastRehearsalTime: '12月14日 15:36',
    avatarColor: 'from-pink-400 to-rose-500'
  }
];

export const mockHistoryStats: HistoryStats = {
  totalRehearsals: 8,
  averageScore: 82,
  bestScore: 92,
  totalDurationMinutes: 120
};

export const mockHistoryRecords: HistoryRecord[] = [
  {
    id: '1',
    dateTime: '2024-12-21 14:30',
    courseName: '新客户开发培训',
    customerName: '外先生',
    customerRole: '27岁 · 互联网产品经理',
    category: '新客户开发',
    duration: '1时53分29秒',
    score: 85,
    scoreLevel: 'good'
  },
  {
    id: '2',
    dateTime: '2024-12-20 10:15',
    courseName: '异议处理训练',
    customerName: '王女士',
    customerRole: '35岁 · 企业法务',
    category: '异议处理',
    duration: '1时29分0秒',
    score: 78,
    scoreLevel: 'average'
  },
  {
    id: '3',
    dateTime: '2024-12-19 16:45',
    courseName: '需求挖掘训练',
    customerName: '李Q',
    customerRole: '47岁 · 企业法务',
    category: '需求挖掘',
    duration: '1时29分08秒',
    score: 92,
    scoreLevel: 'excellent'
  },
  {
    id: '4',
    dateTime: '2024-12-18 14:30',
    courseName: '合同签署训练',
    customerName: '骆小昭',
    customerRole: '29岁 · 设计师',
    category: '合同签署',
    duration: '1时41分58秒',
    score: 82,
    scoreLevel: 'good'
  },
  {
    id: '5',
    dateTime: '2024-12-17 15:30',
    courseName: '新客户开发训练',
    customerName: '用女士',
    customerRole: '45岁 · 财务',
    category: '新客户开发',
    duration: '1时69分40秒',
    score: 80,
    scoreLevel: 'good'
  }
];

export const getCustomers = async (): Promise<CustomerPersona[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockCustomers);
    }, 600);
  });
};

export const getHistory = async (): Promise<{ stats: HistoryStats; records: HistoryRecord[] }> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        stats: mockHistoryStats,
        records: mockHistoryRecords
      });
    }, 700);
  });
};

export const mockTasks: Task[] = [
  {
    id: '1',
    courseName: '新客户开卡邀约话术',
    courseSubtitle: '刘先生（27岁，互联网行业）',
    taskInfo: '第一季新人培训计划',
    taskTag: '新人培训',
    status: 'in-progress',
    timeRange: {
      start: '2024-12-01',
      end: '2024-12-31'
    },
    progress: {
      completed: 3,
      total: 5,
      bestScore: 85
    }
  },
  {
    id: '2',
    courseName: '异议处理训练',
    courseSubtitle: '王女士（35岁，金融行业）',
    taskInfo: '销售技能提升专项',
    taskTag: '技能提升',
    status: 'pending',
    timeRange: {
      start: '2024-12-10',
      end: '2024-12-25'
    },
    progress: {
      completed: 0,
      total: 3
    }
  },
  {
    id: '3',
    courseName: '权益推荐场景',
    courseSubtitle: '李总（42岁，企业高管）',
    taskInfo: '高端客户服务训练',
    taskTag: '高端客户',
    status: 'completed',
    timeRange: {
      start: '2024-11-15',
      end: '2024-11-30'
    },
    progress: {
      completed: 5,
      total: 5,
      bestScore: 92
    }
  },
  {
    id: '4',
    courseName: '合规话术训练',
    courseSubtitle: '张小姐（29岁，设计师）',
    taskInfo: '合规规范强化',
    taskTag: '合规',
    status: 'in-progress',
    timeRange: {
      start: '2024-12-05',
      end: '2024-12-20'
    },
    progress: {
      completed: 2,
      total: 4,
      bestScore: 78
    }
  },
  {
    id: '5',
    courseName: '白金卡销售话术',
    courseSubtitle: '赵先生（38岁，企业主）',
    taskInfo: '产品专项训练',
    taskTag: '产品知识',
    status: 'in-progress',
    timeRange: {
      start: '2024-12-08',
      end: '2024-12-22'
    },
    progress: {
      completed: 1,
      total: 3,
      bestScore: 80
    }
  }
];

export const getTasks = async (): Promise<Task[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockTasks);
    }, 500);
  });
};

export const getStatistics = async (): Promise<Statistics> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockStatistics);
    }, 500);
  });
};
