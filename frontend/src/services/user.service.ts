/**
 * User Service
 *
 * Handles all user-related API calls.
 * Follows Clean Code principles: single responsibility, clear naming, type safety.
 */

import { api } from './api';

// ==================== Type Definitions ====================

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'teacher' | 'student';
  full_name?: string;
  is_active: boolean;
  avatar_url?: string;
  phone?: string;
  organization?: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role?: 'admin' | 'teacher' | 'student';
  full_name?: string;
  phone?: string;
  organization?: string;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  full_name?: string;
  phone?: string;
  organization?: string;
  role?: 'admin' | 'teacher' | 'student';
}

export interface UserListParams {
  role?: string;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserStatistics {
  total_sessions: number;
  completed_sessions: number;
  average_score: number;
  total_training_hours: number;
  courses_enrolled: number;
}

// ==================== Service Implementation ====================

/**
 * User Service
 *
 * Provides methods for user management operations.
 * All methods are async and return Promises for consistent error handling.
 */
export const userService = {
  /**
   * Create a new user (Admin only)
   *
   * @param data - User creation data
   * @returns Promise<User> - Created user
   * @throws Error if creation fails
   */
  createUser: async (data: UserCreate): Promise<User> => {
    return await api.post<User>('/api/v1/users', data);
  },

  /**
   * List users with filtering and pagination (Admin only)
   *
   * @param params - Filter and pagination parameters
   * @returns Promise<UserListResponse> - Paginated user list
   */
  listUsers: async (params?: UserListParams): Promise<UserListResponse> => {
    return await api.get<UserListResponse>('/api/v1/users', { params });
  },

  /**
   * Get user details by ID
   *
   * Users can only access their own data unless they are admin.
   *
   * @param userId - User ID
   * @returns Promise<User> - User details
   * @throws Error if user not found or access denied
   */
  getUser: async (userId: number): Promise<User> => {
    return await api.get<User>(`/api/v1/users/${userId}`);
  },

  /**
   * Update user information
   *
   * Users can only update their own data unless they are admin.
   * Only admins can change roles.
   *
   * @param userId - User ID
   * @param data - Update data
   * @returns Promise<User> - Updated user
   * @throws Error if update fails or access denied
   */
  updateUser: async (userId: number, data: UserUpdate): Promise<User> => {
    return await api.put<User>(`/api/v1/users/${userId}`, data);
  },

  /**
   * Delete user (Admin only)
   *
   * This will also delete all associated sessions and evaluations.
   *
   * @param userId - User ID
   * @returns Promise<void>
   * @throws Error if deletion fails
   */
  deleteUser: async (userId: number): Promise<void> => {
    return await api.delete(`/api/v1/users/${userId}`);
  },

  /**
   * Activate user account (Admin only)
   *
   * @param userId - User ID
   * @returns Promise<User> - Updated user
   */
  activateUser: async (userId: number): Promise<User> => {
    return await api.patch<User>(`/api/v1/users/${userId}/activate`);
  },

  /**
   * Deactivate user account (Admin only)
   *
   * @param userId - User ID
   * @returns Promise<User> - Updated user
   */
  deactivateUser: async (userId: number): Promise<User> => {
    return await api.patch<User>(`/api/v1/users/${userId}/deactivate`);
  },

  /**
   * Get user training statistics
   *
   * Users can only access their own statistics unless they are admin.
   *
   * @param userId - User ID
   * @returns Promise<UserStatistics> - User statistics
   */
  getUserStatistics: async (userId: number): Promise<UserStatistics> => {
    return await api.get<UserStatistics>(`/api/v1/users/${userId}/statistics`);
  }
};
