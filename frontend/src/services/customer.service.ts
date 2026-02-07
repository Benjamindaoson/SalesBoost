
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
  avatarColor: string;
}

// Ensure endpoints match backend mounting (usually /api/v1/customers)
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

  getCustomers: async () => {
    const response = await api.get<CustomerPersona[]>(CUSTOMERS_ENDPOINT);
    return response;
  },

  getCustomer: async (customerId: string) => {
    const response = await api.get<CustomerPersona>(`${CUSTOMERS_ENDPOINT}/${customerId}`);
    return response;
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
