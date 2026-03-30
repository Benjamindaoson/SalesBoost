/**
 * Task Service
 *
 * Handles all task-related API calls.
 * Unifies Admin (CRUD) and Student (Dashboard) functionality.
 */

import { api } from './api';
import { Task as DashboardTask, Statistics } from '@/types/dashboard';

// ==================== Type Definitions (Backend) ====================

export interface BackendTask {
  id: number;
  course_id: number;
  title: string;
  description?: string;
  task_type: 'conversation' | 'quiz' | 'simulation';
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  order: number;
  points: number;
  passing_score: number;
  time_limit_minutes?: number;
  instructions?: string;
  scenario?: Record<string, any>;
  customer_profile?: Record<string, any>;
  created_at: string;
  updated_at: string;
  completion_rate?: number;
  average_score?: number;
}

export interface TaskCreate {
  course_id: number;
  title: string;
  description?: string;
  task_type: 'conversation' | 'quiz' | 'simulation';
  status?: 'locked' | 'available' | 'in_progress' | 'completed';
  order?: number;
  points?: number;
  passing_score?: number;
  time_limit_minutes?: number;
  instructions?: string;
  scenario?: Record<string, any>;
  customer_profile?: Record<string, any>;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  task_type?: 'conversation' | 'quiz' | 'simulation';
  status?: 'locked' | 'available' | 'in_progress' | 'completed';
  order?: number;
  points?: number;
  passing_score?: number;
  time_limit_minutes?: number;
  instructions?: string;
  scenario?: Record<string, any>;
  customer_profile?: Record<string, any>;
}

export interface TaskListParams {
  course_id?: number;
  task_type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface TaskListResponse {
  items: BackendTask[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskStartResponse {
  session_id: string;
  task_id: number;
  message: string;
}

// API endpoints
const TASKS_ENDPOINT = '/api/v1/tasks';
const STATISTICS_ENDPOINT = '/api/v1/statistics';

// ==================== Service Implementation ====================

/**
 * Map backend task status to frontend status
 */
function mapTaskStatus(backendStatus: string): 'pending' | 'in-progress' | 'completed' {
  switch (backendStatus.toLowerCase()) {
    case 'locked':
      return 'pending';
    case 'available':
      return 'pending';
    case 'in_progress':
    case 'active':
      return 'in-progress';
    case 'completed':
      return 'completed';
    default:
      return 'pending';
  }
}

export const taskService = {
  // ==================== Student / Dashboard Methods ====================

  /**
   * Get all tasks for the current user (Mapped for Dashboard)
   * Handles both: tasks_simple (array) and tasks (paginated { items })
   */
  getTasks: async (): Promise<DashboardTask[]> => {
    try {
      const response = await api.get<any>(TASKS_ENDPOINT);
      const items = Array.isArray(response) ? response : (response?.items ?? []);

      // Transform backend response to frontend Task format
      return items.map((item: any) => ({
        id: item.id.toString(),
        courseName: item.title,
        courseSubtitle: item.description || '',
        taskInfo: item.instructions || '',
        taskTag: item.task_type,
        status: mapTaskStatus(item.status),
        timeRange: {
          start: item.created_at,
          end: item.updated_at
        },
        progress: {
          completed: Math.floor((item.completion_rate || 0) / 100 * (item.points || 100)),
          total: item.points || 100,
          bestScore: item.average_score || 0
        }
      }));
    } catch (error) {
      console.error('[TaskService] Failed to fetch tasks:', error);
      return [];
    }
  },

  /**
   * Get statistics for the current user
   */
  getStatistics: async (): Promise<Statistics> => {
    try {
      const response = await api.get<Statistics>(STATISTICS_ENDPOINT);
      return response;
    } catch (error) {
      console.error('[TaskService] Failed to fetch statistics:', error);
      return {
        totalTasks: 0,
        inProgress: 0,
        completed: 0,
        averageScore: 0,
        lockedItems: 0
      };
    }
  },

  /**
   * Get task details by ID (Mapped for Dashboard)
   */
  getTaskById: async (taskId: string): Promise<DashboardTask | null> => {
    try {
      const response = await api.get<any>(`${TASKS_ENDPOINT}/${taskId}`);

      return {
        id: response.id.toString(),
        courseName: response.title,
        courseSubtitle: response.description || '',
        taskInfo: response.instructions || '',
        taskTag: response.task_type,
        status: mapTaskStatus(response.status),
        timeRange: {
          start: response.created_at,
          end: response.updated_at
        },
        progress: {
          completed: Math.floor((response.completion_rate || 0) / 100 * (response.points || 100)),
          total: response.points || 100,
          bestScore: response.average_score || 0
        }
      };
    } catch (error) {
      console.error('[TaskService] Failed to fetch task:', error);
      return null;
    }
  },

  // ==================== Admin / CRUD Methods ====================

  /**
   * Create a new task (Admin only)
   */
  createTask: async (data: TaskCreate): Promise<BackendTask> => {
    return await api.post<BackendTask>(TASKS_ENDPOINT, data);
  },

  /**
   * List tasks with filtering and pagination (Raw Backend Data)
   */
  listTasks: async (params?: TaskListParams): Promise<TaskListResponse> => {
    return await api.get<TaskListResponse>(TASKS_ENDPOINT, { params });
  },

  /**
   * Get task details by ID (Raw Backend Data)
   */
  getTask: async (taskId: number): Promise<BackendTask> => {
    return await api.get<BackendTask>(`${TASKS_ENDPOINT}/${taskId}`);
  },

  /**
   * Update task (Admin only)
   */
  updateTask: async (taskId: number, data: TaskUpdate): Promise<BackendTask> => {
    return await api.put<BackendTask>(`${TASKS_ENDPOINT}/${taskId}`, data);
  },

  /**
   * Delete task (Admin only)
   */
  deleteTask: async (taskId: number): Promise<void> => {
    return await api.delete(`${TASKS_ENDPOINT}/${taskId}`);
  },

  /**
   * Start a task (create a new training session)
   */
  startTask: async (taskId: string | number): Promise<TaskStartResponse> => {
    return await api.post<TaskStartResponse>(`${TASKS_ENDPOINT}/${taskId}/start`);
  }
};

// Export standalone functions for backward compatibility with taskService.ts usage
export const { getTasks, getStatistics, getTaskById, startTask, createTask, updateTask, deleteTask, listTasks, getTask } = taskService;
