import { createClient } from '@supabase/supabase-js';
import { env } from '@/config/env';

/**
 * Supabase client instance
 * Uses validated environment variables from env.ts
 * Will throw error on startup if configuration is invalid
 */
export const supabase = createClient(
  env.VITE_SUPABASE_URL,
  env.VITE_SUPABASE_ANON_KEY,
  {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  }
);
