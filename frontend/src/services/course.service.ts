/**
 * Course Service - Admin & Student
 * Fetches from /api/v1/courses
 */
import { api } from './api';

export interface Course {
  id: number;
  title: string;
  description: string | null;
  difficulty: number;
  duration_minutes: number;
  status: string;
  category: string | null;
  updated_at?: string;
  user_status?: 'not_started' | 'in_progress' | 'completed';
  progress?: number;
}

export interface CourseCategory {
  name: string;
}

export const courseService = {
  list: () => api.get<Course[]>('/api/v1/courses'),
  listUserCourses: async (): Promise<{ items: Course[] }> => {
    const courses = await api.get<Course[] | { items: Course[] }>('/api/v1/courses');
    if (Array.isArray(courses)) return { items: courses };
    return courses as { items: Course[] };
  },
  get: (id: number) => api.get<Course>(`/api/v1/courses/${id}`),
  listCategories: () => api.get<string[]>('/api/v1/courses/categories'),
};
