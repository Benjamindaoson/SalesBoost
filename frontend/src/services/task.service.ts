/**
 * Task Service
 *
 * Handles all task-related API calls.
 * Follows Clean Code principles: single responsibility, clear naming, type safety.
 */

import { api } from './api';

// ==================== Type Definitions ====================

export interface Task {
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
  items: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskStartResponse {
  session_id: string;
  task_id: number;
  message: string;
}

// ==================== Service Implementation ====================

/**
 * Task Service
 *
 * Provides methods for task management operations.
 * All methods are async and return Promises for consistent error handling.
 */
export const taskService = {
  /**
   * Create a new task (Admin only)
   *
   * @param data - Task creation data
   * @returns Promise<Task> - Created task
   * @throws Error if creation fails
   */
  createTask: async (data: TaskCreate): Promise<Task> => {
    return await api.post<Task>('/api/v1/tasks', data);
  },

  /**
   * List tasks with filtering and pagination
   *
   * @param params - Filter and pagination parameters
   * @returns Promise<TaskListResponse> - Paginated task list
   */
  listTasks: async (params?: TaskListParams): Promise<TaskListResponse> => {
    return await api.get<TaskListResponse>('/api/v1/tasks', { params });
  },

  /**
   * Get task details by ID
   *
   * @param taskId - Task ID
   * @returns Promise<Task> - Task details with statistics
   * @throws Error if task not found
   */
  getTask: async (taskId: number): Promise<Task> => {
    return await api.get<Task>(`/api/v1/tasks/${taskId}`);
  },

  /**
   * Update task (Admin only)
   *
   * @param taskId - Task ID
   * @param data - Update data
   * @returns Promise<Task> - Updated task
   * @throws Error if update fails
   */
  updateTask: async (taskId: number, data: TaskUpdate): Promise<Task> => {
    return await api.put<Task>(`/api/v1/tasks/${taskId}`, data);
  },

  /**
   * Delete task (Admin only)
   *
   * This will also delete all associated sessions.
   *
   * @param taskId - Task ID
   * @returns Promise<void>
   * @throws Error if deletion fails
   */
  deleteTask: async (taskId: number): Promise<void> => {
    return await api.delete(`/api/v1/tasks/${taskId}`);
  },

  /**
   * Start a task (create a new training session)
   *
   * This creates a new session for the user to begin the task.
   *
   * @param taskId - Task ID
   * @returns Promise<TaskStartResponse> - Session information
   * @throws Error if task is locked or start fails
   */
  startTask: async (taskId: number): Promise<TaskStartResponse> => {
    return await api.post<TaskStartResponse>(`/api/v1/tasks/${taskId}/start`);
  }
};
