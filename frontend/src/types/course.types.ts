export interface CustomerProfile {
  name: string;
  avatar?: string;
  occupation?: string;
  personality?: string;
  background?: string;
  painPoints?: string[];
  goals?: string[];
}

export interface EvaluationCriteria {
  dimensions: {
    id: string;
    name: string;
    weight: number; // 0-100
    description?: string;
  }[];
}

export interface Course {
  id: string;
  title: string;
  description?: string;
  customer_profile: CustomerProfile;
  evaluation_criteria: EvaluationCriteria;
  is_active: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}
