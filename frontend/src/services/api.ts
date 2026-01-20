import { mockTasks, mockTaskStats, mockPersonas, mockPracticeRecords, mockPracticeStats } from "@/mocks/data";
import { TaskFilter, HistoryFilter } from "@/types";

export const taskService = {
  getStats: async () => {
    return Promise.resolve(mockTaskStats);
  },
  getTasks: async (filter?: TaskFilter) => {
    let tasks = [...mockTasks];
    if (filter?.status && filter.status !== 'all') {
      tasks = tasks.filter(t => filter.status === 'in_progress' ? t.status === 'in_progress' : 
                               filter.status === 'not_started' ? t.status === 'not_started' :
                               filter.status === 'completed' ? t.status === 'completed' : true);
    }
    return Promise.resolve(tasks);
  },
};

export const personaService = {
  getPersonas: async () => {
    return Promise.resolve(mockPersonas);
  },
};

export const historyService = {
  getStats: async () => {
    return Promise.resolve(mockPracticeStats);
  },
  getHistory: async (filter?: HistoryFilter) => {
    return Promise.resolve(mockPracticeRecords);
  },
};
