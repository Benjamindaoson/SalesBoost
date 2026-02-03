import { z } from 'zod';

/**
 * Environment variable schema with Zod validation
 * Ensures all required environment variables are present and valid
 * Fails fast on application startup if configuration is invalid
 */
const envSchema = z.object({
  // Supabase Configuration (REQUIRED)
  VITE_SUPABASE_URL: z.string().url('VITE_SUPABASE_URL must be a valid URL'),
  VITE_SUPABASE_ANON_KEY: z.string().min(1, 'VITE_SUPABASE_ANON_KEY is required'),

  // API Configuration (OPTIONAL - defaults provided)
  VITE_API_URL: z.string().url().optional().default('http://localhost:8000/api/v1'),
  VITE_WS_URL: z.string().optional().default('ws://localhost:8000/ws'),
  VITE_DEEPSEEK_API_KEY: z.string().optional(),
  VITE_DEEPSEEK_BASE_URL: z.string().optional(),

  // Monitoring & Analytics (OPTIONAL)
  VITE_SENTRY_DSN: z.string().url().optional(),
  VITE_POSTHOG_KEY: z.string().optional(),
  VITE_POSTHOG_HOST: z.string().url().optional(),

  // Feature Flags (OPTIONAL)
  VITE_ENABLE_AI_FEATURES: z.enum(['true', 'false']).optional().default('false'),
  VITE_ENABLE_ANALYTICS: z.enum(['true', 'false']).optional().default('true'),
  VITE_ENABLE_ERROR_REPORTING: z.enum(['true', 'false']).optional().default('true'),

  // Environment Mode
  MODE: z.enum(['development', 'production', 'test']),
  DEV: z.boolean(),
  PROD: z.boolean(),
});

/**
 * Parse and validate environment variables
 * Throws detailed error if validation fails
 */
function parseEnv() {
  try {
    return envSchema.parse({
      VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
      VITE_SUPABASE_ANON_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY,
      VITE_API_URL: import.meta.env.VITE_API_URL,
      VITE_WS_URL: import.meta.env.VITE_WS_URL,
      VITE_DEEPSEEK_API_KEY: import.meta.env.VITE_DEEPSEEK_API_KEY,
      VITE_DEEPSEEK_BASE_URL: import.meta.env.VITE_DEEPSEEK_BASE_URL,
      VITE_SENTRY_DSN: import.meta.env.VITE_SENTRY_DSN,
      VITE_POSTHOG_KEY: import.meta.env.VITE_POSTHOG_KEY,
      VITE_POSTHOG_HOST: import.meta.env.VITE_POSTHOG_HOST,
      VITE_ENABLE_AI_FEATURES: import.meta.env.VITE_ENABLE_AI_FEATURES,
      VITE_ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS,
      VITE_ENABLE_ERROR_REPORTING: import.meta.env.VITE_ENABLE_ERROR_REPORTING,
      MODE: import.meta.env.MODE,
      DEV: import.meta.env.DEV,
      PROD: import.meta.env.PROD,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      const missingVars = error.errors.map((err: z.ZodIssue) => `  - ${err.path.join('.')}: ${err.message}`).join('\n');

      throw new Error(
        `❌ Invalid environment configuration:\n\n${missingVars}\n\n` +
        `Please check your .env file and ensure all required variables are set.\n` +
        `See .env.example for reference.`
      );
    }
    throw error;
  }
}

/**
 * Validated and type-safe environment variables
 * Use this instead of import.meta.env for type safety
 */
export const env = parseEnv();

/**
 * Type-safe environment variable access
 */
export type Env = z.infer<typeof envSchema>;

/**
 * Helper functions for feature flags
 */
export const features = {
  aiEnabled: env.VITE_ENABLE_AI_FEATURES === 'true',
  analyticsEnabled: env.VITE_ENABLE_ANALYTICS === 'true',
  errorReportingEnabled: env.VITE_ENABLE_ERROR_REPORTING === 'true',
} as const;

/**
 * Helper to check if running in production
 */
export const isProd = env.MODE === 'production';
export const isDev = env.MODE === 'development';
export const isTest = env.MODE === 'test';
