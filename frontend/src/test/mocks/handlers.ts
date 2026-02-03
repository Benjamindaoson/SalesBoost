import { http, HttpResponse } from 'msw';

const API_URL = 'http://localhost:8000/api/v1';

/**
 * MSW request handlers for API mocking
 * Add handlers for all backend endpoints used in tests
 */
export const handlers = [
  // Auth endpoints
  http.get(`${API_URL}/auth/me`, () => {
    return HttpResponse.json({
      id: 'test-user-id',
      email: 'test@example.com',
      user_metadata: { role: 'student' },
    });
  }),

  // Session endpoints
  http.post(`${API_URL}/sessions`, () => {
    return HttpResponse.json({
      id: 'session-123',
      user_id: 'test-user-id',
      scenario_id: 'scenario-1',
      status: 'active',
      created_at: new Date().toISOString(),
    });
  }),

  http.get(`${API_URL}/sessions`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'session-1',
          scenario_id: 'scenario-1',
          status: 'completed',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
    });
  }),

  http.get(`${API_URL}/sessions/:id`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      scenario_id: 'scenario-1',
      status: 'completed',
      created_at: '2024-01-01T00:00:00Z',
    });
  }),

  http.get(`${API_URL}/sessions/:id/review`, ({ params }) => {
    return HttpResponse.json({
      session_id: params.id,
      skill_improvement: {
        opening: 85,
        discovery: 78,
        presentation: 82,
        objection: 75,
        closing: 88,
        followup: 80,
      },
      strategy_timeline: [],
      effective_adoptions: [],
    });
  }),

  // Course endpoints
  http.get(`${API_URL}/admin/courses`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'course-1',
          title: 'B2B Sales Fundamentals',
          modules: 5,
          active: true,
          last_updated: '2024-01-01',
        },
        {
          id: 'course-2',
          title: 'Advanced Negotiation',
          modules: 8,
          active: true,
          last_updated: '2024-01-02',
        },
      ],
      total: 2,
    });
  }),

  http.get(`${API_URL}/admin/courses/:id`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      title: 'B2B Sales Fundamentals',
      modules: 5,
      active: true,
      last_updated: '2024-01-01',
    });
  }),

  // Scenario endpoints
  http.get(`${API_URL}/scenarios`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'scenario-1',
          title: 'Enterprise Software Sale',
          difficulty: 'medium',
          course_id: 'course-1',
        },
      ],
      total: 1,
    });
  }),

  // Knowledge endpoints
  http.get(`${API_URL}/knowledge`, () => {
    return HttpResponse.json({
      items: [],
      total: 0,
    });
  }),

  http.post(`${API_URL}/knowledge/upload`, () => {
    return HttpResponse.json({
      id: 'knowledge-1',
      filename: 'test.txt',
      status: 'uploaded',
    });
  }),

  // Analytics endpoints
  http.get(`${API_URL}/admin/analytics`, () => {
    return HttpResponse.json({
      total_cost_usd: 125.50,
      active_users_7d: 42,
      competency_index: 78.5,
      cost_trend_7d: [
        { date: '2024-01-01', cost: 15.2 },
        { date: '2024-01-02', cost: 18.5 },
      ],
      skill_averages: {
        opening: 82,
        discovery: 75,
        closing: 88,
      },
      token_usage: {
        input_tokens: 150000,
        output_tokens: 75000,
      },
    });
  }),

  // Evolution trends endpoints
  http.get(`${API_URL}/evolution-trends`, () => {
    return HttpResponse.json({
      models: [
        {
          id: 'model-1',
          name: 'GPT-4',
          status: 'active',
          quality_score: 0.92,
          intent_distribution: { sales: 0.6, support: 0.4 },
        },
      ],
    });
  }),

  // Error scenarios for testing
  http.get(`${API_URL}/error/401`, () => {
    return new HttpResponse(null, { status: 401 });
  }),

  http.get(`${API_URL}/error/500`, () => {
    return new HttpResponse(null, { status: 500 });
  }),
];
