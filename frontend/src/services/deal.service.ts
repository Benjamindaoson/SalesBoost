/**
 * Deal Service
 *
 * API client for deals, encounters, pipeline, methodology, and copilot.
 */

import { api } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Deal {
  id: number;
  tenant_id: string;
  owner_id: number;
  customer_name: string;
  customer_company?: string;
  customer_title?: string;
  customer_info?: string;
  amount: number;
  stage: string;
  methodology_framework: string;
  methodology_state?: MethodologyStateData;
  methodology_score: number;
  expected_close_date?: string;
  close_reason?: string;
  encounter_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface DimensionState {
  status: 'unknown' | 'partial' | 'confirmed';
  evidence: string;
  updated_at: string;
}

export interface MethodologyStateData {
  framework: string;
  dimensions: Record<string, DimensionState>;
  overall_score: number;
  next_focus: string | null;
}

export interface MethodologyDetail {
  framework: string;
  framework_label: string;
  dimensions: Record<string, DimensionState>;
  overall_score: number;
  next_focus: string | null;
  gaps: GapItem[];
}

export interface GapItem {
  dimension: string;
  label: string;
  status: string;
  weight: number;
  description: string;
  probe_questions: string[];
}

export interface Encounter {
  id: number;
  deal_id: number;
  session_id?: number;
  encounter_type: string;
  summary?: string;
  methodology_before?: MethodologyStateData;
  methodology_after?: MethodologyStateData;
  action_items?: string;
  created_at?: string;
}

export interface FunnelItem {
  stage: string;
  label: string;
  count: number;
  total_amount: number;
}

export interface PrepPrompt {
  prompt: string;
  methodology_state: MethodologyStateData;
  gaps: GapItem[];
}

export interface CopilotSuggestion {
  content: string;
  tactic: string;
  confidence: number;
  rationale: string;        // NEW: AI explanation for why this tactic was recommended
}

export interface CopilotResponse {
  suggestions: CopilotSuggestion[];
  methodology_context?: Record<string, unknown>;
  detected_stage: string;
  stage_confidence: number;      // NEW: model confidence in stage detection (0-1)
  detected_dimensions: string[];
  methodology_gaps: string[];    // NEW: MEDDPICC dimension keys to address
  // Intent (NEW)
  intent_type: string;           // OBJECTION | BUYING_SIGNAL | DISCOVERY | ...
  intent_confidence: number;
  intent_reasoning: string;      // Chain-of-thought visible in UI
  personalized: boolean;         // NEW: true if rep weakness profile was injected
}

export interface CockpitOverview {
  funnel: FunnelItem[];
  today: {
    encounters_today: number;
    new_deals_today: number;
    stage_advances_today: number;
    deals_won_today: number;
    deals_lost_today: number;
  };
  prediction: {
    predicted_amount: number;
    confidence: number;
    target_amount: number;
    target_pct: number;
  };
  methodology: {
    avg_score: number;
    total_deals: number;
    dimension_stats: { dimension: string; label: string; avg_pct: number }[];
    weakest: string | null;
    insight: string | null;
  };
  recent_events: {
    id: number;
    event_type: string;
    payload?: Record<string, unknown>;
    created_at: string;
  }[];
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export const dealService = {
  // Deals
  list: (stage?: string) =>
    api.get<Deal[]>(`/api/v1/deals${stage ? `?stage=${stage}` : ''}`),

  get: (id: number) =>
    api.get<Deal>(`/api/v1/deals/${id}`),

  create: (data: {
    customer_name: string;
    customer_company?: string;
    customer_title?: string;
    customer_info?: string;
    amount?: number;
    methodology_framework?: string;
  }) => api.post<Deal>('/api/v1/deals', data),

  update: (id: number, data: Partial<Deal>) =>
    api.put<Deal>(`/api/v1/deals/${id}`, data),

  delete: (id: number) =>
    api.delete(`/api/v1/deals/${id}`),

  // Methodology
  getMethodology: (dealId: number) =>
    api.get<MethodologyDetail>(`/api/v1/deals/${dealId}/methodology`),

  updateDimension: (dealId: number, dimension: string, status: string, evidence: string = '') =>
    api.put(`/api/v1/deals/${dealId}/methodology/dimensions`, { dimension, status, evidence }),

  getPrepPrompt: (dealId: number) =>
    api.get<PrepPrompt>(`/api/v1/deals/${dealId}/prep-prompt`),

  // Encounters
  listEncounters: (dealId: number) =>
    api.get<Encounter[]>(`/api/v1/deals/${dealId}/encounters`),

  createEncounter: (dealId: number, data: {
    encounter_type: string;
    session_id?: number;
    summary?: string;
    action_items?: string;
  }) => api.post<Encounter>(`/api/v1/deals/${dealId}/encounters`, data),

  // Pipeline
  getFunnel: () =>
    api.get<FunnelItem[]>('/api/v1/pipeline/funnel'),

  // Frameworks reference
  listFrameworks: () =>
    api.get<{ id: string; label: string }[]>('/api/v1/methodology/frameworks'),

  // Copilot
  copilotSuggest: (data: {
    deal_id?: number;
    customer_message: string;
    mode?: string;
  }) => api.post<CopilotResponse>('/api/v1/copilot/suggest', data),

  copilotPrep: (dealId: number) =>
    api.post<{ battle_plan: string; methodology_state: MethodologyStateData; key_gaps: GapItem[]; talking_points: string[] }>(
      '/api/v1/copilot/prep', { deal_id: dealId }
    ),

  // Cockpit
  getCockpitOverview: () =>
    api.get<CockpitOverview>('/api/v1/cockpit/overview'),
};
