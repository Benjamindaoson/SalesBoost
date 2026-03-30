import { api } from './api';
import { mockCustomers } from './mockData';

export interface CustomerCreate {
  name: string;
  age: number;
  job: string;
  traits: string[];
  description: string;
  avatar_color?: string;
  scenario_id: string; // Required for backend linkage
}

export interface CustomerUpdate extends Partial<CustomerCreate> {
  id: string;
}

export interface CustomerPersona {
  id: string;
  name: string;
  age: number;
  job: string;
  traits: string[];
  description: string;
  creator: string;
  rehearsalCount: number;
  lastRehearsalTime: string;
  avatarColor?: string;
}

/** Backend customers_simple schema (seed personas) */
interface BackendPersona {
  id: number;
  name: string;
  role: string;
  company: string;
  industry: string;
  pain_points: string[];
  personality: string;
  difficulty: number;
  avatar_url?: string | null;
}

/** Map backend seed personas to frontend CustomerPersona */
function mapBackendToFrontend(p: BackendPersona): CustomerPersona {
  return {
    id: String(p.id),
    name: p.name,
    age: 0,
    job: p.role,
    traits: p.pain_points.length ? p.pain_points : [p.personality],
    description: `${p.company} · ${p.industry} · ${p.personality}`,
    creator: '系统',
    rehearsalCount: 0,
    lastRehearsalTime: '',
    avatarColor: 'from-purple-200 to-purple-400',
  };
}

const CUSTOMERS_ENDPOINT = '/api/v1/customers';

export const getCustomersMock = async (): Promise<CustomerPersona[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockCustomers);
    }, 500);
  });
};

export const customerService = {
  createCustomer: async (data: CustomerCreate) => {
    const response = await api.post<CustomerPersona>(CUSTOMERS_ENDPOINT, data);
    return response;
  },

  getCustomers: async (): Promise<CustomerPersona[]> => {
    const response = await api.get<BackendPersona[] | CustomerPersona[]>(CUSTOMERS_ENDPOINT);
    const arr = Array.isArray(response) ? response : [];
    if (arr.length > 0) {
      const first = arr[0] as any;
      if (typeof first.role === 'string' && typeof first.company === 'string') {
        return (arr as BackendPersona[]).map(mapBackendToFrontend);
      }
    }
    return (arr as CustomerPersona[]).map((p) => ({
      ...p,
      avatarColor: p.avatarColor ?? 'from-purple-200 to-purple-400',
    }));
  },

  getCustomer: async (customerId: string): Promise<CustomerPersona> => {
    const response = await api.get<BackendPersona | CustomerPersona>(`${CUSTOMERS_ENDPOINT}/${customerId}`);
    const r = response as any;
    if (r?.role && r?.company) {
      return mapBackendToFrontend(r as BackendPersona);
    }
    return r as CustomerPersona;
  },

  updateCustomer: async (customerId: string, data: Partial<CustomerCreate>) => {
    const response = await api.patch<CustomerPersona>(`${CUSTOMERS_ENDPOINT}/${customerId}`, data);
    return response;
  },

  deleteCustomer: async (customerId: string) => {
    const response = await api.delete<{ message: string }>(`${CUSTOMERS_ENDPOINT}/${customerId}`);
    return response;
  }
};
