import { z } from 'zod';

/**
 * General settings schema
 */
export const settingsSchema = z.object({
  platform_name: z
    .string()
    .min(1, 'Platform name is required')
    .max(100, 'Platform name must be less than 100 characters'),
  support_email: z
    .string()
    .email('Invalid email address')
    .optional(),
  max_session_duration: z
    .number()
    .int('Must be a whole number')
    .min(5, 'Minimum 5 minutes')
    .max(180, 'Maximum 180 minutes')
    .optional(),
  enable_notifications: z.boolean().default(true),
  enable_analytics: z.boolean().default(true),
});

export type SettingsFormData = z.infer<typeof settingsSchema>;

/**
 * Integration settings schema
 */
export const integrationSchema = z.object({
  name: z.string().min(1, 'Integration name is required'),
  api_key: z.string().min(1, 'API key is required'),
  api_secret: z.string().optional(),
  enabled: z.boolean().default(false),
  config: z.record(z.string(), z.any()).optional(),
});

export type IntegrationFormData = z.infer<typeof integrationSchema>;
