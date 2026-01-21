import { mockTasks, mockTaskStats, mockPersonas, mockPracticeRecords, mockPracticeStats } from "@/mocks/data";
import { TaskFilter, HistoryFilter } from "@/types";

// Base API URL handling
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Helper for making requests
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
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
    // Fallback to mock data if API fails (for demo stability if backend is down)
    throw error; 
  }
}

export const taskService = {
  getStats: async () => {
    // TODO: Implement backend endpoint
    // return request<any>("/tasks/stats");
    return Promise.resolve(mockTaskStats);
  },
  getTasks: async (filter?: TaskFilter) => {
    // TODO: Implement backend endpoint
    // const query = new URLSearchParams(filter as any).toString();
    // return request<any>(`/tasks?${query}`);
    
    // Using mock for now as backend endpoints might not fully match frontend model yet
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
    // TODO: Implement backend endpoint
    // return request<any>("/personas");
    return Promise.resolve(mockPersonas);
  },
};

export const historyService = {
  getStats: async () => {
    // TODO: Implement backend endpoint
    return Promise.resolve(mockPracticeStats);
  },
  getHistory: async (filter?: HistoryFilter) => {
    // TODO: Implement backend endpoint
    return Promise.resolve(mockPracticeRecords);
  },
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
