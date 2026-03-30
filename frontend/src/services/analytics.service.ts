
/**
 * Analytics Service - Real API Integration
 */

import { api } from './api';

const ANALYTICS_ENDPOINT = '/api/v1/admin/analytics';

export interface CostTrendPoint {
    date: string;
    cost_usd: number;
    input_tokens: number;
    output_tokens: number;
}

export interface SkillAverages {
    opening: number;
    discovery: number;
    closing: number;
}

export interface AnalyticsOverview {
    total_cost_usd: number;
    total_input_tokens: number;
    total_output_tokens: number;
    active_users_7d: number;
    total_practice_seconds_7d: number;
    competency_index: number;
    skill_averages: SkillAverages;
    cost_trend: CostTrendPoint[];
}

export const analyticsService = {
    /**
     * Get Admin Analytics Overview
     */
    async getOverview(): Promise<AnalyticsOverview> {
        try {
            const response = await api.get<AnalyticsOverview>(ANALYTICS_ENDPOINT);
            return response;
        } catch (error) {
            console.error('[AnalyticsService] Failed to fetch overview:', error);
            // Return safe default
            return {
                total_cost_usd: 0,
                total_input_tokens: 0,
                total_output_tokens: 0,
                active_users_7d: 0,
                total_practice_seconds_7d: 0,
                competency_index: 0,
                skill_averages: { opening: 0, discovery: 0, closing: 0 },
                cost_trend: []
            };
        }
    }
};
