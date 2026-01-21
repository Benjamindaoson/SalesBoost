import { mockTasks, mockTaskStats, mockPersonas, mockPracticeRecords, mockPracticeStats } from "@/mocks/data";
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

export const taskService = {
  getStats: async () => {
    try {
      return await request<any>("/reports/stats/tasks");
    } catch {
      return Promise.resolve(mockTaskStats);
    }
  },
  getTasks: async (filter?: TaskFilter) => {
    try {
      const query = new URLSearchParams(filter as any).toString();
      return await request<any[]>(`/reports/tasks?${query}`);
    } catch {
       let tasks = [...mockTasks];
       if (filter?.status && filter.status !== 'all') {
         tasks = tasks.filter(t => filter.status === 'in_progress' ? t.status === 'in_progress' : 
                                  filter.status === 'not_started' ? t.status === 'not_started' :
                                  filter.status === 'completed' ? t.status === 'completed' : true);
       }
       return Promise.resolve(tasks);
    }
  },
};

export const personaService = {
  getPersonas: async () => {
    try {
      // Assuming backend has a personas endpoint, or we map scenarios to personas
      // For now, let's keep mock if backend endpoint doesn't strictly exist, 
      // but let's try to fetch scenarios if possible.
      // return await request<any>("/scenarios"); 
      // Reverting to mock for personas as scenarios API might differ in structure
      return Promise.resolve(mockPersonas);
    } catch {
      return Promise.resolve(mockPersonas);
    }
  },
};

export const historyService = {
  getStats: async () => {
    try {
      return await request<any>("/reports/stats/practice");
    } catch {
      return Promise.resolve(mockPracticeStats);
    }
  },
  getHistory: async (filter?: HistoryFilter) => {
    try {
      const query = new URLSearchParams(filter as any).toString();
      return await request<any[]>(`/sessions?${query}`);
    } catch {
      return Promise.resolve(mockPracticeRecords);
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
