import { describe, it, expect, vi, beforeEach } from 'vitest';
import { taskService } from './api';

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('taskService', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorage.clear();
  });

  it('getStats fetches from API and returns data on success', async () => {
    const mockData = { total: 10, completed: 5 };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    });

    const result = await taskService.getStats();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/reports/stats/tasks'),
      expect.objectContaining({ headers: expect.any(Object) })
    );
    expect(result).toEqual(mockData);
  });

  it('getStats falls back to mock data on error', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network Error'));
    const result = await taskService.getStats();
    // Should return mock data structure
    expect(result).toHaveProperty('total');
    expect(result).toHaveProperty('inProgress');
  });
});
