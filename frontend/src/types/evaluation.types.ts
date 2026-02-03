export interface DimensionScore {
  score: number;
  feedback?: string;
}

export interface ImprovementSuggestion {
  category: string;
  suggestion: string;
  actionable_items: string[];
}

export interface Evaluation {
  id: string;
  session_id: string;
  dimension_scores: Record<string, DimensionScore>;
  overall_feedback?: string;
  improvement_suggestions?: ImprovementSuggestion[];
  created_at: string;
}
