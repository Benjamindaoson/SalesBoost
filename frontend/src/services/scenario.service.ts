
import { api } from './api';

export interface Persona {
  id: string;
  name: string;
  occupation?: string;
  age_range?: string;
  personality_traits?: string;
  communication_style?: string;
  difficulty_level: string;
}

export interface Scenario {
  id: string;
  course_id: string;
  name: string;
  description?: string;
  product_category: string;
  difficulty_level: string;
  max_turns: number;
  personas: Persona[];
}

// Ensure endpoints match backend mounting (usually /api/v1/scenarios)
const SCENARIOS_ENDPOINT = '/api/v1/scenarios';

export const scenarioService = {
  listScenarios: async (params?: { course_id?: string; difficulty?: string }) => {
    const response = await api.get<{ items: Scenario[]; total: number }>(SCENARIOS_ENDPOINT, { params });
    return response;
  },

  getScenario: async (scenarioId: string) => {
    const response = await api.get<Scenario>(`${SCENARIOS_ENDPOINT}/${scenarioId}`);
    return response;
  }
};
