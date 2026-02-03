/**
 * Course Service
 *
 * Handles all course-related API calls
 */

import { api } from './api';

export interface Course {
  id: number;
  title: string;
  description?: string;
  status: 'draft' | 'published' | 'archived';
  category?: string;
  difficulty: number;
  duration_minutes?: number;
  thumbnail_url?: string;
  instructor_name?: string;
  learning_objectives?: string[];
  prerequisites?: string[];
  tags?: string[];
  created_at: string;
  updated_at: string;
}

export interface CourseCreate {
  title: string;
  description?: string;
  status?: 'draft' | 'published' | 'archived';
  category?: string;
  difficulty?: number;
  duration_minutes?: number;
  thumbnail_url?: string;
  instructor_name?: string;
  learning_objectives?: string[];
  prerequisites?: string[];
  tags?: string[];
}

export interface CourseListParams {
  status?: string;
  category?: string;
  difficulty?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface CourseListResponse {
  items: Course[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskSummary {
  id: number;
  title: string;
  task_type: string;
  status: string;
  order: number;
  points: number;
}

export const courseService = {
  /**
   * Create a new course (Admin only)
   */
  createCourse: async (data: CourseCreate): Promise<Course> => {
    return await api.post<Course>('/api/v1/courses', data);
  },

  /**
   * List courses with filtering and pagination
   */
  listCourses: async (params?: CourseListParams): Promise<CourseListResponse> => {
    return await api.get<CourseListResponse>('/api/v1/courses', { params });
  },

  listUserCourses: async (params?: CourseListParams): Promise<CourseListResponse> => {
    return await api.get<CourseListResponse>('/api/v1/courses', { params });
  },

  /**
   * Get course details
   */
  getCourse: async (courseId: number): Promise<Course> => {
    return await api.get<Course>(`/api/v1/courses/${courseId}`);
  },

  /**
   * Update course (Admin only)
   */
  updateCourse: async (courseId: number, data: Partial<CourseCreate>): Promise<Course> => {
    return await api.put<Course>(`/api/v1/courses/${courseId}`, data);
  },

  /**
   * Delete course (Admin only)
   */
  deleteCourse: async (courseId: number): Promise<void> => {
    return await api.delete(`/api/v1/courses/${courseId}`);
  },

  /**
   * Get tasks for a course
   */
  getCourseTasks: async (courseId: number): Promise<TaskSummary[]> => {
    return await api.get<TaskSummary[]>(`/api/v1/courses/${courseId}/tasks`);
  }
};
