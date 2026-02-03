import { setupServer } from 'msw/node';
import { handlers } from './handlers';

/**
 * MSW server for API mocking in tests
 * Intercepts HTTP requests and returns mock responses
 */
export const server = setupServer(...handlers);
