// Mock data imports removed - using real API endpoints
import { TaskFilter, HistoryFilter } from "@/types";

// Base API URL handling
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Helper for making requests
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers as Record<string, string>,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Handle unauthorized (e.g., redirect to login)
        // window.location.href = "/login"; // Only if we are not already there
      }
      throw new Error(`API Error: ${response.statusText}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    console.error("Request failed:", error);
    throw error;
  }
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at?: string;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  is_system: boolean;
}

export const adminService = {
  getUsers: async (role?: string) => {
    const query = role ? `?role=${role}` : "";
    return await request<User[]>(`/admin/users${query}`);
  },
  createUser: async (userData: any) => {
    return await request<User>("/admin/users", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  },
  updateUser: async (userId: string, userData: any) => {
    return await request<User>(`/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(userData),
    });
  },
  deleteUser: async (userId: string) => {
    return await request<void>(`/admin/users/${userId}`, {
      method: "DELETE",
    });
  },
  updateUserStatus: async (userId: string, isActive: boolean) => {
    return await request<User>(`/admin/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
  },
  getRoles: async () => {
    return await request<Role[]>("/admin/roles");
  },
};

export const taskService = {
  getStats: async () => {
    return await request<any>("/reports/stats/tasks");
  },
  getTasks: async (filter?: TaskFilter) => {
    const query = new URLSearchParams(filter as any).toString();
    return await request<any[]>(`/reports/tasks?${query}`);
  },
};

export const personaService = {
  getPersonas: async () => {
    try {
      // Fetch scenarios from API
      const response = await request<any>("/scenarios");
      
      // Handle both array and paginated response
      const items = Array.isArray(response) ? response : (response.items || []);
      
      // Map scenarios to Persona format expected by UI
      return items.map((scenario: any) => ({
        id: scenario.id,
        name: scenario.name,
        description: scenario.description || "暂无描述",
        avatar: "/favicon.svg",
        tags: [scenario.product_category, scenario.difficulty_level],
        lastPracticed: "从未练习", // Placeholder as backend doesn't track this yet
        note: `难度: ${scenario.difficulty_level}`
      }));
    } catch (error) {
      console.error("Failed to fetch personas:", error);
      return []; // Return empty array instead of throwing
    }
  },
};

export const historyService = {
  getStats: async () => {
    try {
      // Backend doesn't have /reports/stats/practice yet, use task stats for now or mock
      // Ideally we should implement this endpoint in backend
      return await request<any>("/reports/stats/tasks"); 
    } catch {
       return {
         totalSessions: 0,
         averageScore: 0,
         highestScore: 0,
         totalDuration: 0
       };
    }
  },
  getHistory: async (filter?: HistoryFilter) => {
    try {
      const query = new URLSearchParams(filter as any).toString();
      const response = await request<any>(`/sessions?${query}`);
      
      const items = response.items || [];
      
      // Map session items to HistoryRecord format
      return items.map((session: any) => ({
        id: session.id,
        dateTime: new Date(session.started_at).toLocaleString(),
        courseInfo: "实战演练", // Generic
        customerRole: "客户", // Generic
        category: "销售技巧",
        duration: "15分钟", // Placeholder
        score: session.final_score || 0
      }));
    } catch (error) {
      console.error("Failed to fetch history:", error);
      return [];
    }
  },
  getSession: async (sessionId: string) => {
    return await request<any>(`/sessions/${sessionId}`);
  }
};

export const authService = {
  login: async (username: string) => {
    // Simple login for MVP
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", "any"); // Backend uses dummy password check for now?

    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      body: formData, // OAuth2PasswordRequestForm expects form data
    });

    if (!response.ok) {
      throw new Error("Login failed");
    }

    const data = await response.json();
    localStorage.setItem("auth_token", data.access_token);
    return data;
  },
  logout: () => {
    localStorage.removeItem("auth_token");
  },
  isAuthenticated: () => {
    return !!localStorage.getItem("auth_token");
  }
};
