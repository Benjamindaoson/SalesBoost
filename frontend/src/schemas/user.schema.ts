import { z } from 'zod';

/**
 * Login form schema
 */
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Invalid email address'),
});

export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * User form schema (for admin user management)
 */
export const userSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(100, 'Name must be less than 100 characters')
    .optional(),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Invalid email address'),
  role: z.enum(['admin', 'student', 'operator']),
  team: z
    .string()
    .max(50, 'Team name must be less than 50 characters')
    .optional(),
});

export type UserFormData = z.infer<typeof userSchema>;

/**
 * User update schema (partial fields)
 */
export const userUpdateSchema = userSchema.partial().extend({
  id: z.string().min(1, 'User ID is required'),
});

export type UserUpdateFormData = z.infer<typeof userUpdateSchema>;
