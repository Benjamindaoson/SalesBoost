import { z } from 'zod';

/**
 * Course form schema
 */
export const courseSchema = z.object({
  title: z
    .string()
    .min(3, 'Title must be at least 3 characters')
    .max(200, 'Title must be less than 200 characters'),
  description: z
    .string()
    .max(1000, 'Description must be less than 1000 characters')
    .optional(),
  modules: z
    .number()
    .int('Modules must be a whole number')
    .min(1, 'Must have at least 1 module')
    .max(100, 'Cannot exceed 100 modules'),
  active: z.boolean().default(true),
  difficulty: z
    .enum(['beginner', 'intermediate', 'advanced'])
    .optional(),
  duration_hours: z
    .number()
    .positive('Duration must be positive')
    .max(1000, 'Duration cannot exceed 1000 hours')
    .optional(),
});

export type CourseFormData = z.infer<typeof courseSchema>;

/**
 * Course update schema (partial fields)
 */
export const courseUpdateSchema = courseSchema.partial().extend({
  id: z.string().min(1, 'Course ID is required'),
});

export type CourseUpdateFormData = z.infer<typeof courseUpdateSchema>;
